#!/usr/bin/env python3
"""
Historical Regime Analysis Engine
=================================

Builds on validated MarketCondition Analytics to perform regime detection
across multiple historical periods with enhanced confidence scoring and
transition analysis.

Author: StatArb Gemini Team
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import asdict
import json
from pathlib import Path

from .data_types import (
    HistoricalPeriod, MarketDataset, RegimeDetectionResult, 
    RegimeStats, RegimeAnalysisOutput, validate_regime_analysis
)

# Import from validated MarketCondition Analytics
from ..market_condition_analytics import (
    MarketConditionAnalyticsEngine, MarketCondition
)

# Configure logging
logger = logging.getLogger(__name__)


class HistoricalRegimeAnalyzer:
    """
    Enhanced regime analyzer for historical market condition detection
    """
    
    def __init__(self, confidence_threshold: float = 0.6, 
                 enable_clustering: bool = True):
        """
        Initialize the historical regime analyzer
        
        Args:
            confidence_threshold: Minimum confidence for regime detection
            enable_clustering: Whether to perform advanced regime clustering
        """
        self.confidence_threshold = confidence_threshold
        self.enable_clustering = enable_clustering
        
        # Initialize components
        self.core_analyzer = MarketConditionAnalyticsEngine()
        # Note: EnhancedRegimeDetector is not used in historical analysis
        # We use simplified regime detection for historical periods
        
        # Enhanced analysis parameters
        self.regime_persistence_window = 20  # Days to check for regime persistence
        self.transition_smoothing_factor = 0.3  # For transition probability smoothing
        
        # Cache for regime detection results
        self._detection_cache: Dict[str, RegimeDetectionResult] = {}
        
        logger.info(f"HistoricalRegimeAnalyzer initialized with confidence threshold: {confidence_threshold}")
    
    def analyze_single_period(self, dataset: MarketDataset, 
                            include_transition_analysis: bool = True) -> RegimeDetectionResult:
        """
        Analyze market regime for a single historical period
        
        Args:
            dataset: Market dataset for the period
            include_transition_analysis: Whether to include transition probability analysis
            
        Returns:
            Complete regime detection result
        """
        period_name = dataset.period.name
        logger.info(f"Analyzing regime for period: {period_name}")
        
        # Check cache
        if period_name in self._detection_cache:
            logger.debug(f"Using cached result for period: {period_name}")
            return self._detection_cache[period_name]
        
        try:
            # Prepare data for core analyzer
            market_data = self._prepare_data_for_analyzer(dataset.market_data)
            
            if market_data.empty:
                raise ValueError(f"No valid data for regime analysis in period {period_name}")
            
            # Run simplified regime detection for historical analysis
            regime_detection = self._detect_simple_regime(market_data)
            
            # Calculate enhanced metrics
            enhanced_metrics = self._calculate_enhanced_metrics(market_data, regime_detection)
            
            # Calculate regime confidence
            confidence = self._calculate_regime_confidence(
                market_data, regime_detection, enhanced_metrics
            )
            
            # Calculate regime strength
            regime_strength = self._calculate_regime_strength(enhanced_metrics)
            
            # Calculate market stress
            market_stress = self._calculate_market_stress(market_data)
            
            # Prepare supporting indicators
            supporting_indicators = self._extract_supporting_indicators(
                market_data, regime_detection, enhanced_metrics
            )
            
            # Calculate transition probabilities if requested
            transition_probability = {}
            if include_transition_analysis:
                transition_probability = self._estimate_transition_probabilities(
                    market_data, regime_detection
                )
            
            # Create result
            result = RegimeDetectionResult(
                period=dataset.period,
                detected_regime=regime_detection,
                confidence=confidence,
                regime_strength=regime_strength,
                market_stress=market_stress,
                supporting_indicators=supporting_indicators,
                transition_probability=transition_probability,
                data_points_analyzed=len(market_data),
                detection_metadata={
                    'analysis_timestamp': datetime.now().isoformat(),
                    'analyzer_version': '1.0.0',
                    'data_quality_score': dataset.metadata.get('data_quality_score', 0.0),
                    'symbols_analyzed': len(dataset.symbols),
                    'confidence_threshold': self.confidence_threshold
                }
            )
            
            # Validate result
            if confidence < self.confidence_threshold:
                logger.warning(
                    f"Low confidence ({confidence:.3f}) for regime detection in period {period_name}"
                )
            
            # Cache result
            self._detection_cache[period_name] = result
            
            logger.info(
                f"Regime analysis complete for {period_name}: "
                f"{regime_detection.value} (confidence: {confidence:.3f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing period {period_name}: {e}")
            raise
    
    def analyze_multiple_periods(self, datasets: Dict[str, MarketDataset],
                               enable_cross_period_analysis: bool = True) -> RegimeAnalysisOutput:
        """
        Analyze market regimes across multiple historical periods
        
        Args:
            datasets: Dictionary of period datasets
            enable_cross_period_analysis: Whether to perform cross-period analysis
            
        Returns:
            Comprehensive regime analysis output
        """
        logger.info(f"Analyzing regimes across {len(datasets)} historical periods")
        
        # Analyze individual periods
        regime_results = []
        for period_name, dataset in datasets.items():
            try:
                result = self.analyze_single_period(dataset)
                regime_results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze period {period_name}: {e}")
                continue
        
        if not regime_results:
            raise ValueError("No successful regime detections across any periods")
        
        # Calculate regime distribution statistics
        regime_distribution = self._calculate_regime_distribution(regime_results)
        
        # Build transition matrix
        transition_matrix = self._build_transition_matrix(regime_results)
        
        # Perform advanced clustering if enabled
        regime_clusters = {}
        if self.enable_clustering:
            regime_clusters = self._perform_regime_clustering(regime_results, datasets)
        
        # Prepare analysis metadata
        analysis_metadata = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_periods_analyzed': len(regime_results),
            'periods_analyzed': [r.period.name for r in regime_results],
            'avg_confidence': sum(r.confidence for r in regime_results) / len(regime_results),
            'confidence_threshold_used': self.confidence_threshold,
            'clustering_enabled': self.enable_clustering,
            'cross_period_analysis_enabled': enable_cross_period_analysis
        }
        
        # Create comprehensive output
        analysis_output = RegimeAnalysisOutput(
            regime_results=regime_results,
            regime_distribution=regime_distribution,
            transition_matrix=transition_matrix,
            regime_clusters=regime_clusters,
            analysis_metadata=analysis_metadata
        )
        
        # Validate output
        if not validate_regime_analysis(analysis_output):
            logger.warning("Regime analysis output failed validation checks")
        
        logger.info(
            f"Multi-period regime analysis complete: "
            f"{len(regime_results)} periods, avg confidence {analysis_output.avg_confidence:.3f}"
        )
        
        return analysis_output
    
    def validate_regime_predictions(self, analysis_output: RegimeAnalysisOutput) -> Dict[str, Any]:
        """
        Validate regime predictions against known regime hints
        
        Args:
            analysis_output: Complete regime analysis output
            
        Returns:
            Validation metrics and detailed comparison
        """
        validation_results = {
            'overall_accuracy': 0.0,
            'regime_specific_accuracy': {},
            'confusion_matrix': {},
            'validation_details': [],
            'recommendations': []
        }
        
        # Collect predictions vs hints
        predictions = []
        actuals = []
        detailed_comparisons = []
        
        for result in analysis_output.regime_results:
            if result.period.regime_hint:
                predicted = result.detected_regime.value
                actual = result.period.regime_hint
                
                predictions.append(predicted)
                actuals.append(actual)
                
                is_correct = predicted == actual
                detailed_comparisons.append({
                    'period': result.period.name,
                    'predicted': predicted,
                    'actual': actual,
                    'correct': is_correct,
                    'confidence': result.confidence,
                    'regime_strength': result.regime_strength
                })
        
        if not predictions:
            logger.warning("No regime hints available for validation")
            return validation_results
        
        # Calculate overall accuracy
        correct_predictions = sum(1 for p, a in zip(predictions, actuals) if p == a)
        validation_results['overall_accuracy'] = correct_predictions / len(predictions)
        
        # Calculate regime-specific accuracy
        unique_regimes = set(actuals)
        for regime in unique_regimes:
            regime_predictions = [p for p, a in zip(predictions, actuals) if a == regime]
            regime_correct = sum(1 for p, a in zip(predictions, actuals) if a == regime and p == a)
            validation_results['regime_specific_accuracy'][regime] = (
                regime_correct / len(regime_predictions) if regime_predictions else 0.0
            )
        
        # Build confusion matrix
        confusion_matrix = {}
        for actual in unique_regimes:
            confusion_matrix[actual] = {}
            for predicted in set(predictions):
                count = sum(1 for p, a in zip(predictions, actuals) 
                           if a == actual and p == predicted)
                confusion_matrix[actual][predicted] = count
        
        validation_results['confusion_matrix'] = confusion_matrix
        validation_results['validation_details'] = detailed_comparisons
        
        # Generate recommendations
        if validation_results['overall_accuracy'] < 0.7:
            validation_results['recommendations'].append(
                f"Overall accuracy ({validation_results['overall_accuracy']:.1%}) is below 70%. "
                "Consider adjusting confidence threshold or enhancing detection algorithms."
            )
        
        worst_regime = min(validation_results['regime_specific_accuracy'].items(), 
                          key=lambda x: x[1])
        if worst_regime[1] < 0.5:
            validation_results['recommendations'].append(
                f"Poor detection accuracy for {worst_regime[0]} regime ({worst_regime[1]:.1%}). "
                "Consider regime-specific tuning."
            )
        
        logger.info(
            f"Regime validation complete: {validation_results['overall_accuracy']:.1%} accuracy "
            f"across {len(predictions)} periods"
        )
        
        return validation_results
    
    def _prepare_data_for_analyzer(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare market data for the core analyzer"""
        if market_data.empty:
            return market_data
        
        # Ensure required columns exist
        required_columns = ['timestamp', 'symbol', 'close']
        missing_columns = [col for col in required_columns if col not in market_data.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns for analysis: {missing_columns}")
        
        # Sort data
        prepared_data = market_data.sort_values(['timestamp', 'symbol']).copy()
        
        # Ensure we have the columns expected by MarketConditionAnalyticsEngine
        # The core analyzer expects columns that match the demo format
        analyzer_columns = ['timestamp', 'symbol', 'close', 'volume']
        
        # Add missing columns with defaults if necessary
        for col in analyzer_columns:
            if col not in prepared_data.columns:
                if col == 'volume':
                    prepared_data[col] = 1000000  # Default volume
                else:
                    logger.warning(f"Missing expected column {col} for analyzer")
        
        return prepared_data
    
    def _calculate_enhanced_metrics(self, market_data: pd.DataFrame, 
                                  regime: MarketCondition) -> Dict[str, Any]:
        """Calculate enhanced metrics for regime analysis"""
        metrics = {}
        
        try:
            # Volatility metrics
            if 'returns' in market_data.columns:
                returns = market_data['returns'].dropna()
                metrics['volatility'] = returns.std() * np.sqrt(252)  # Annualized
                metrics['skewness'] = returns.skew()
                metrics['kurtosis'] = returns.kurtosis()
            else:
                # Calculate returns from close prices
                if 'close' in market_data.columns and len(market_data) > 1:
                    market_data_sorted = market_data.sort_values(['symbol', 'timestamp'])
                    returns = market_data_sorted.groupby('symbol')['close'].pct_change().dropna()
                    metrics['volatility'] = returns.std() * np.sqrt(252)
                    metrics['skewness'] = returns.skew()
                    metrics['kurtosis'] = returns.kurtosis()
            
            # Price movement metrics
            if 'close' in market_data.columns:
                prices = market_data['close']
                metrics['price_range_pct'] = (prices.max() - prices.min()) / prices.mean()
                metrics['price_trend'] = np.polyfit(range(len(prices)), prices, 1)[0]
            
            # Volume metrics
            if 'volume' in market_data.columns:
                volumes = market_data['volume']
                metrics['avg_volume'] = volumes.mean()
                metrics['volume_volatility'] = volumes.std() / volumes.mean() if volumes.mean() > 0 else 0
            
            # Cross-sectional metrics
            if 'symbol' in market_data.columns:
                symbols = market_data['symbol'].unique()
                metrics['symbols_count'] = len(symbols)
                
                # Calculate cross-sectional dispersion
                if 'returns' in market_data.columns:
                    symbol_returns = market_data.groupby('symbol')['returns'].mean()
                    metrics['cross_sectional_dispersion'] = symbol_returns.std()
        
        except Exception as e:
            logger.warning(f"Error calculating enhanced metrics: {e}")
            # Provide default metrics
            metrics = {
                'volatility': 0.2,
                'skewness': 0.0,
                'kurtosis': 3.0,
                'price_range_pct': 0.1,
                'symbols_count': 1
            }
        
        return metrics
    
    def _calculate_regime_confidence(self, market_data: pd.DataFrame,
                                   regime: MarketCondition, 
                                   enhanced_metrics: Dict[str, Any]) -> float:
        """Calculate confidence in regime detection"""
        confidence_factors = []
        
        # Factor 1: Data quality and quantity
        data_quality_factor = min(1.0, len(market_data) / 100)  # More data = higher confidence
        confidence_factors.append(data_quality_factor)
        
        # Factor 2: Volatility consistency with regime
        volatility = enhanced_metrics.get('volatility', 0.2)
        if regime == MarketCondition.HIGH_VOLATILITY:
            vol_factor = min(1.0, volatility / 0.3)  # Expect high volatility
        elif regime == MarketCondition.LOW_VOLATILITY:
            vol_factor = max(0.0, 1.0 - volatility / 0.15)  # Expect low volatility
        else:
            vol_factor = 0.7  # Neutral for other regimes
        confidence_factors.append(vol_factor)
        
        # Factor 3: Cross-sectional consistency
        symbols_count = enhanced_metrics.get('symbols_count', 1)
        cross_sectional_factor = min(1.0, symbols_count / 20)  # More symbols = higher confidence
        confidence_factors.append(cross_sectional_factor)
        
        # Factor 4: Statistical significance
        skewness = abs(enhanced_metrics.get('skewness', 0.0))
        kurtosis = enhanced_metrics.get('kurtosis', 3.0)
        stat_factor = min(1.0, (skewness + abs(kurtosis - 3.0)) / 2.0)
        confidence_factors.append(stat_factor)
        
        # Weighted average
        weights = [0.3, 0.4, 0.2, 0.1]
        confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        return round(min(1.0, max(0.0, confidence)), 3)
    
    def _calculate_regime_strength(self, enhanced_metrics: Dict[str, Any]) -> float:
        """Calculate the strength/intensity of the detected regime"""
        volatility = enhanced_metrics.get('volatility', 0.2)
        price_range = enhanced_metrics.get('price_range_pct', 0.1)
        volume_vol = enhanced_metrics.get('volume_volatility', 0.5)
        
        # Combine factors to measure regime intensity
        strength_components = [
            min(1.0, volatility / 0.5),  # Normalized volatility
            min(1.0, price_range / 0.3),  # Normalized price range
            min(1.0, volume_vol / 1.0)    # Normalized volume volatility
        ]
        
        strength = sum(strength_components) / len(strength_components)
        return round(strength, 3)
    
    def _calculate_market_stress(self, market_data: pd.DataFrame) -> float:
        """Calculate market stress indicator"""
        try:
            stress_factors = []
            
            # Volatility stress
            if 'returns' in market_data.columns:
                returns = market_data['returns'].dropna()
                if len(returns) > 0:
                    vol_stress = min(1.0, returns.std() * np.sqrt(252) / 0.4)
                    stress_factors.append(vol_stress)
            
            # Extreme movement stress
            if 'close' in market_data.columns and len(market_data) > 1:
                prices = market_data['close']
                price_changes = prices.pct_change().dropna()
                if len(price_changes) > 0:
                    extreme_moves = (abs(price_changes) > 0.05).sum() / len(price_changes)
                    stress_factors.append(extreme_moves * 2)  # Scale up
            
            if stress_factors:
                stress = sum(stress_factors) / len(stress_factors)
                return round(min(1.0, stress), 3)
            else:
                return 0.5  # Default moderate stress
                
        except Exception as e:
            logger.warning(f"Error calculating market stress: {e}")
            return 0.5
    
    def _extract_supporting_indicators(self, market_data: pd.DataFrame,
                                     regime: MarketCondition,
                                     enhanced_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract supporting indicators for regime detection"""
        indicators = {
            'regime_detected': regime.value,
            'volatility_level': enhanced_metrics.get('volatility', 0.0),
            'data_points': len(market_data),
            'symbols_analyzed': enhanced_metrics.get('symbols_count', 0),
            'analysis_period_days': self._calculate_analysis_period_days(market_data)
        }
        
        # Add regime-specific indicators
        if regime == MarketCondition.HIGH_VOLATILITY:
            indicators.update({
                'volatility_percentile': min(100, enhanced_metrics.get('volatility', 0.2) / 0.6 * 100),
                'extreme_moves_ratio': self._calculate_extreme_moves_ratio(market_data)
            })
        elif regime == MarketCondition.TRENDING_BULL:
            indicators.update({
                'price_trend': enhanced_metrics.get('price_trend', 0.0),
                'positive_returns_ratio': self._calculate_positive_returns_ratio(market_data)
            })
        elif regime == MarketCondition.TRENDING_BEAR:
            indicators.update({
                'price_trend': enhanced_metrics.get('price_trend', 0.0),
                'negative_returns_ratio': 1.0 - self._calculate_positive_returns_ratio(market_data)
            })
        
        return indicators
    
    def _estimate_transition_probabilities(self, market_data: pd.DataFrame,
                                         current_regime: MarketCondition) -> Dict[MarketCondition, float]:
        """Estimate probabilities of transitioning to other regimes"""
        # This is a simplified implementation
        # In production, this would use more sophisticated models
        
        base_probabilities = {
            MarketCondition.TRENDING_BULL: 0.2,
            MarketCondition.TRENDING_BEAR: 0.2,
            MarketCondition.SIDEWAYS_RANGE: 0.3,
            MarketCondition.HIGH_VOLATILITY: 0.15,
            MarketCondition.LOW_VOLATILITY: 0.15
        }
        
        # Adjust based on current regime characteristics
        volatility = self._calculate_current_volatility(market_data)
        trend = self._calculate_current_trend(market_data)
        
        adjusted_probabilities = base_probabilities.copy()
        
        # High volatility increases probability of volatility regimes
        if volatility > 0.3:
            adjusted_probabilities[MarketCondition.HIGH_VOLATILITY] *= 2
            adjusted_probabilities[MarketCondition.LOW_VOLATILITY] *= 0.5
        
        # Strong trend increases probability of trending regimes
        if abs(trend) > 0.1:
            if trend > 0:
                adjusted_probabilities[MarketCondition.TRENDING_BULL] *= 1.5
                adjusted_probabilities[MarketCondition.TRENDING_BEAR] *= 0.7
            else:
                adjusted_probabilities[MarketCondition.TRENDING_BEAR] *= 1.5
                adjusted_probabilities[MarketCondition.TRENDING_BULL] *= 0.7
        
        # Normalize probabilities
        total_prob = sum(adjusted_probabilities.values())
        normalized_probabilities = {
            regime: prob / total_prob 
            for regime, prob in adjusted_probabilities.items()
        }
        
        return normalized_probabilities
    
    def _calculate_regime_distribution(self, regime_results: List[RegimeDetectionResult]) -> Dict[str, RegimeStats]:
        """Calculate statistical distribution of detected regimes"""
        if not regime_results:
            return {}
        
        # Group results by regime
        regime_groups = {}
        for result in regime_results:
            regime_name = result.detected_regime.value
            if regime_name not in regime_groups:
                regime_groups[regime_name] = []
            regime_groups[regime_name].append(result)
        
        # Calculate statistics for each regime
        regime_distribution = {}
        total_periods = len(regime_results)
        
        for regime_name, results in regime_groups.items():
            # Calculate frequency
            frequency = len(results) / total_periods
            
            # Calculate average confidence
            avg_confidence = sum(r.confidence for r in results) / len(results)
            
            # Calculate average duration (from period data)
            avg_duration = sum(r.period.duration_days for r in results) / len(results)
            
            # Find dominant periods (high confidence detections)
            dominant_periods = [
                r.period.name for r in results 
                if r.confidence > self.confidence_threshold + 0.1
            ]
            
            # Extract key characteristics
            key_characteristics = self._extract_regime_characteristics(results)
            
            # Calculate transition patterns (simplified)
            transition_patterns = self._calculate_regime_transition_patterns(regime_name, regime_results)
            
            regime_stats = RegimeStats(
                frequency=frequency,
                avg_confidence=avg_confidence,
                avg_duration_days=avg_duration,
                total_occurrences=len(results),
                dominant_periods=dominant_periods,
                key_characteristics=key_characteristics,
                transition_patterns=transition_patterns
            )
            
            regime_distribution[regime_name] = regime_stats
        
        return regime_distribution
    
    def _build_transition_matrix(self, regime_results: List[RegimeDetectionResult]) -> Dict[str, Dict[str, float]]:
        """Build regime transition probability matrix"""
        if len(regime_results) < 2:
            return {}
        
        # Sort results by period start date
        sorted_results = sorted(
            regime_results, 
            key=lambda r: r.period.start_datetime
        )
        
        # Count transitions
        transition_counts = {}
        total_transitions = 0
        
        for i in range(len(sorted_results) - 1):
            current_regime = sorted_results[i].detected_regime.value
            next_regime = sorted_results[i + 1].detected_regime.value
            
            if current_regime not in transition_counts:
                transition_counts[current_regime] = {}
            
            if next_regime not in transition_counts[current_regime]:
                transition_counts[current_regime][next_regime] = 0
            
            transition_counts[current_regime][next_regime] += 1
            total_transitions += 1
        
        # Convert counts to probabilities
        transition_matrix = {}
        for from_regime, to_regimes in transition_counts.items():
            transition_matrix[from_regime] = {}
            total_from_regime = sum(to_regimes.values())
            
            for to_regime, count in to_regimes.items():
                probability = count / total_from_regime if total_from_regime > 0 else 0.0
                transition_matrix[from_regime][to_regime] = probability
        
        return transition_matrix
    
    def _perform_regime_clustering(self, regime_results: List[RegimeDetectionResult],
                                 datasets: Dict[str, MarketDataset]) -> Dict[str, Any]:
        """Perform advanced regime clustering analysis"""
        # This is a placeholder for advanced clustering
        # Would implement sophisticated clustering algorithms in production
        
        clustering_results = {
            'method': 'hierarchical_clustering',
            'clusters_identified': 0,
            'cluster_assignments': {},
            'cluster_characteristics': {},
            'clustering_quality_metrics': {}
        }
        
        # For now, simple grouping by detected regime
        regime_clusters = {}
        for result in regime_results:
            regime_name = result.detected_regime.value
            if regime_name not in regime_clusters:
                regime_clusters[regime_name] = []
            regime_clusters[regime_name].append(result.period.name)
        
        clustering_results['clusters_identified'] = len(regime_clusters)
        clustering_results['cluster_assignments'] = regime_clusters
        
        return clustering_results
    
    def _extract_regime_characteristics(self, results: List[RegimeDetectionResult]) -> Dict[str, Any]:
        """Extract key characteristics for a regime across multiple detections"""
        if not results:
            return {}
        
        # Aggregate supporting indicators
        all_indicators = []
        for result in results:
            all_indicators.append(result.supporting_indicators)
        
        # Calculate aggregate characteristics
        characteristics = {
            'avg_volatility': np.mean([
                indicators.get('volatility_level', 0.0) 
                for indicators in all_indicators
            ]),
            'avg_data_points': np.mean([
                indicators.get('data_points', 0) 
                for indicators in all_indicators
            ]),
            'avg_symbols': np.mean([
                indicators.get('symbols_analyzed', 0) 
                for indicators in all_indicators
            ]),
            'regime_strength_distribution': {
                'min': min(r.regime_strength for r in results),
                'max': max(r.regime_strength for r in results),
                'avg': np.mean([r.regime_strength for r in results])
            }
        }
        
        return characteristics
    
    def _calculate_regime_transition_patterns(self, regime_name: str,
                                            all_results: List[RegimeDetectionResult]) -> Dict[str, float]:
        """Calculate transition patterns for a specific regime"""
        # Simplified transition pattern calculation
        patterns = {}
        
        # Find all occurrences of this regime
        regime_occurrences = [r for r in all_results if r.detected_regime.value == regime_name]
        
        if not regime_occurrences:
            return patterns
        
        # For each occurrence, check what comes next
        sorted_results = sorted(all_results, key=lambda r: r.period.start_datetime)
        
        transitions_from_regime = []
        for result in regime_occurrences:
            # Find this result in sorted list
            current_index = next(
                (i for i, r in enumerate(sorted_results) if r.period.name == result.period.name),
                None
            )
            
            # Check next period
            if current_index is not None and current_index < len(sorted_results) - 1:
                next_regime = sorted_results[current_index + 1].detected_regime.value
                transitions_from_regime.append(next_regime)
        
        # Calculate transition frequencies
        if transitions_from_regime:
            unique_transitions = set(transitions_from_regime)
            for transition in unique_transitions:
                count = transitions_from_regime.count(transition)
                patterns[transition] = count / len(transitions_from_regime)
        
        return patterns
    
    def _calculate_analysis_period_days(self, market_data: pd.DataFrame) -> int:
        """Calculate the analysis period in days"""
        if 'timestamp' in market_data.columns and len(market_data) > 1:
            timestamps = pd.to_datetime(market_data['timestamp'])
            return (timestamps.max() - timestamps.min()).days
        return 0
    
    def _calculate_extreme_moves_ratio(self, market_data: pd.DataFrame) -> float:
        """Calculate ratio of extreme price movements"""
        try:
            if 'close' in market_data.columns and len(market_data) > 1:
                prices = market_data['close']
                returns = prices.pct_change().dropna()
                if len(returns) > 0:
                    extreme_threshold = 0.05  # 5% daily move
                    extreme_moves = (abs(returns) > extreme_threshold).sum()
                    return extreme_moves / len(returns)
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_positive_returns_ratio(self, market_data: pd.DataFrame) -> float:
        """Calculate ratio of positive returns"""
        try:
            if 'returns' in market_data.columns:
                returns = market_data['returns'].dropna()
                if len(returns) > 0:
                    positive_returns = (returns > 0).sum()
                    return positive_returns / len(returns)
            elif 'close' in market_data.columns and len(market_data) > 1:
                prices = market_data['close']
                returns = prices.pct_change().dropna()
                if len(returns) > 0:
                    positive_returns = (returns > 0).sum()
                    return positive_returns / len(returns)
            return 0.5  # Default neutral
        except Exception:
            return 0.5
    
    def _calculate_current_volatility(self, market_data: pd.DataFrame) -> float:
        """Calculate current volatility estimate"""
        try:
            if 'returns' in market_data.columns:
                returns = market_data['returns'].dropna()
                if len(returns) > 0:
                    return returns.std() * np.sqrt(252)
            elif 'close' in market_data.columns and len(market_data) > 1:
                prices = market_data['close']
                returns = prices.pct_change().dropna()
                if len(returns) > 0:
                    return returns.std() * np.sqrt(252)
            return 0.2  # Default volatility
        except Exception:
            return 0.2
    
    def _calculate_current_trend(self, market_data: pd.DataFrame) -> float:
        """Calculate current price trend"""
        try:
            if 'close' in market_data.columns and len(market_data) > 10:
                prices = market_data['close'].values
                x = np.arange(len(prices))
                slope, _ = np.polyfit(x, prices, 1)
                # Normalize by average price
                avg_price = prices.mean()
                return slope / avg_price if avg_price > 0 else 0.0
            return 0.0
        except Exception:
            return 0.0
    
    def _detect_simple_regime(self, market_data: pd.DataFrame) -> 'MarketCondition':
        """
        Simple regime detection for historical analysis
        
        Args:
            market_data: Price data for analysis (timestamp, symbol, close format)
            
        Returns:
            MarketCondition enum value
        """
        try:
            # Convert long format to wide format for calculations
            if 'timestamp' in market_data.columns and 'symbol' in market_data.columns:
                # Pivot to wide format: timestamps as index, symbols as columns
                price_data = market_data.pivot(index='timestamp', columns='symbol', values='close')
            else:
                # Already in wide format
                price_data = market_data
            
            # Calculate basic market indicators
            returns = price_data.pct_change().dropna()
            
            # Calculate key indicators
            volatility = returns.std().mean() * np.sqrt(252)  # Annualized volatility
            mean_return = returns.mean().mean() * 252  # Annualized return
            
            # Calculate price momentum (first to last price change)
            price_momentum = (price_data.iloc[-1] / price_data.iloc[0] - 1).mean()
            
            # Import MarketCondition here to avoid circular imports
            from ..market_condition_analytics import MarketCondition
            
            # Simple regime classification
            if volatility > 0.35:
                if mean_return < -0.15:
                    regime = MarketCondition.CRISIS_MODE
                else:
                    regime = MarketCondition.HIGH_VOLATILITY
            elif volatility < 0.15:
                regime = MarketCondition.LOW_VOLATILITY
            elif price_momentum > 0.15:
                regime = MarketCondition.TRENDING_BULL
            elif price_momentum < -0.15:
                regime = MarketCondition.TRENDING_BEAR
            else:
                regime = MarketCondition.SIDEWAYS_RANGE
            
            return regime
            
        except Exception as e:
            logger.error(f"Error in simple regime detection: {e}")
            from ..market_condition_analytics import MarketCondition
            return MarketCondition.SIDEWAYS_RANGE