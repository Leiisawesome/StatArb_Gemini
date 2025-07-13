"""
Phase 3 Integration: Performance Feedback Integration System
===========================================================

This module integrates all Phase 3 components into a unified performance feedback
and adaptive learning system that continuously improves statistical arbitrage
performance through intelligent feedback loops and optimization.

Components Integrated:
- Performance Feedback Loop
- Adaptive Screening Weights
- Success Pattern Learning
- Dynamic Threshold Adjustment

Author: Pro Quant Desk Trader
Date: 2024
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Import Phase 3 components
from .performance_feedback_loop import PerformanceFeedbackLoop, PerformanceRecord, FeedbackEvent
from .adaptive_screening_weights import AdaptiveScreeningWeights, PairSelectionResult, MarketRegime
from .success_pattern_learning import SuccessPatternLearning, PatternPrediction, SuccessPattern
from .dynamic_threshold_adjustment import DynamicThresholdAdjustment, OptimizationResult, ThresholdType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationStatus(Enum):
    """Status of the integrated system"""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    OPTIMIZING = "OPTIMIZING"
    LEARNING = "LEARNING"
    ADAPTING = "ADAPTING"
    ERROR = "ERROR"
    STOPPED = "STOPPED"

class LearningPhase(Enum):
    """Learning phases of the system"""
    BOOTSTRAP = "BOOTSTRAP"
    EXPLORATION = "EXPLORATION"
    EXPLOITATION = "EXPLOITATION"
    REFINEMENT = "REFINEMENT"
    MASTERY = "MASTERY"

@dataclass
class IntegratedPerformanceMetrics:
    """Comprehensive performance metrics across all components"""
    timestamp: datetime
    
    # Overall system performance
    system_sharpe_ratio: float
    system_max_drawdown: float
    system_win_rate: float
    system_profit_factor: float
    
    # Component-specific metrics
    feedback_loop_effectiveness: float
    weight_adaptation_score: float
    pattern_learning_accuracy: float
    threshold_optimization_score: float
    
    # Integration metrics
    component_synchronization: float
    learning_convergence: float
    adaptation_speed: float
    
    # Market context
    market_regime: str
    volatility_regime: str
    
    # Learning progress
    learning_phase: LearningPhase
    learning_progress: float

@dataclass
class IntegratedRecommendation:
    """Integrated recommendation from all components"""
    recommendation_id: str
    pair_id: str
    timestamp: datetime
    
    # Component recommendations
    feedback_recommendations: List[str]
    weight_recommendations: List[str]
    pattern_recommendations: List[str]
    threshold_recommendations: List[str]
    
    # Integrated recommendation
    final_recommendation: str
    confidence: float
    expected_impact: float
    
    # Implementation details
    priority: str
    implementation_complexity: str
    expected_implementation_time: timedelta
    
    # Validation
    recommendation_validated: bool = False
    actual_impact: Optional[float] = None

class Phase3IntegratedSystem:
    """
    Comprehensive Phase 3 Performance Feedback Integration System
    
    This class integrates all Phase 3 components:
    - Performance Feedback Loop for continuous improvement
    - Adaptive Screening Weights for dynamic pair selection
    - Success Pattern Learning for predictive modeling
    - Dynamic Threshold Adjustment for parameter optimization
    
    Provides unified learning, adaptation, and optimization capabilities.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the integrated Phase 3 system
        
        Args:
            config: Configuration dictionary for all components
        """
        self.config = config or {}
        
        # Initialize components
        self.feedback_loop = PerformanceFeedbackLoop(
            db_path=self.config.get('feedback_db_path', 'feedback_integration.db'),
            learning_window=self.config.get('learning_window', 252),
            min_performance_samples=self.config.get('min_performance_samples', 50)
        )
        
        self.adaptive_weights = AdaptiveScreeningWeights(
            db_path=self.config.get('weights_db_path', 'weights_integration.db'),
            optimization_frequency=self.config.get('optimization_frequency', 7),
            min_performance_samples=self.config.get('min_performance_samples', 50)
        )
        
        self.pattern_learning = SuccessPatternLearning(
            db_path=self.config.get('patterns_db_path', 'patterns_integration.db'),
            min_pattern_samples=self.config.get('min_pattern_samples', 100),
            retraining_frequency=self.config.get('retraining_frequency', 7)
        )
        
        self.threshold_adjustment = DynamicThresholdAdjustment(
            db_path=self.config.get('thresholds_db_path', 'thresholds_integration.db'),
            optimization_frequency=self.config.get('optimization_frequency', 7),
            min_performance_samples=self.config.get('min_performance_samples', 50)
        )
        
        # System state
        self.system_status = IntegrationStatus.INITIALIZING
        self.learning_phase = LearningPhase.BOOTSTRAP
        self.learning_progress = 0.0
        
        # Integrated metrics
        self.integrated_metrics: List[IntegratedPerformanceMetrics] = []
        self.integrated_recommendations: List[IntegratedRecommendation] = []
        
        # Cross-component learning
        self.component_correlations: Dict[str, float] = {}
        self.learning_synergies: Dict[str, float] = {}
        
        # Callbacks
        self.integration_callbacks: List[Callable[[IntegratedPerformanceMetrics], None]] = []
        self.recommendation_callbacks: List[Callable[[IntegratedRecommendation], None]] = []
        
        # Threading
        self.integration_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize component callbacks
        self._setup_component_callbacks()
        
        # Initialize cross-component learning
        self._initialize_cross_component_learning()
        
        self.system_status = IntegrationStatus.RUNNING
        
        logger.info("Phase 3 integrated system initialized")
    
    def _setup_component_callbacks(self):
        """Set up callbacks for component integration"""
        # Feedback loop callbacks
        self.feedback_loop.add_feedback_callback(self._handle_feedback_event)
        self.feedback_loop.add_adjustment_callback(self._handle_adjustment_event)
        
        # Adaptive weights callbacks
        self.adaptive_weights.add_optimization_callback(self._handle_weight_optimization)
        
        # Pattern learning callbacks
        self.pattern_learning.add_pattern_discovery_callback(self._handle_pattern_discovery)
        self.pattern_learning.add_prediction_callback(self._handle_pattern_prediction)
        
        # Threshold adjustment callbacks
        self.threshold_adjustment.add_optimization_callback(self._handle_threshold_optimization)
        self.threshold_adjustment.add_threshold_update_callback(self._handle_threshold_update)
    
    def _initialize_cross_component_learning(self):
        """Initialize cross-component learning mechanisms"""
        try:
            # Initialize component correlation tracking
            self.component_correlations = {
                'feedback_weights': 0.0,
                'feedback_patterns': 0.0,
                'feedback_thresholds': 0.0,
                'weights_patterns': 0.0,
                'weights_thresholds': 0.0,
                'patterns_thresholds': 0.0
            }
            
            # Initialize learning synergies
            self.learning_synergies = {
                'feedback_adaptation': 0.0,
                'weight_pattern_synergy': 0.0,
                'threshold_feedback_synergy': 0.0,
                'global_optimization': 0.0
            }
            
            logger.info("Cross-component learning initialized")
            
        except Exception as e:
            logger.error(f"Error initializing cross-component learning: {e}")
    
    def _handle_feedback_event(self, event: FeedbackEvent):
        """Handle feedback events from the feedback loop"""
        try:
            # Update adaptive weights based on feedback
            if event.signal.value in ['NEGATIVE', 'STRONG_NEGATIVE']:
                # Inform adaptive weights about poor performance
                self._inform_adaptive_weights_about_performance(event.pair_id, False)
            elif event.signal.value in ['POSITIVE', 'STRONG_POSITIVE']:
                # Inform adaptive weights about good performance
                self._inform_adaptive_weights_about_performance(event.pair_id, True)
            
            # Update pattern learning with feedback
            self._update_pattern_learning_with_feedback(event)
            
            # Update threshold adjustment based on feedback
            self._update_threshold_adjustment_with_feedback(event)
            
            # Update component correlations
            self._update_component_correlations('feedback', event)
            
        except Exception as e:
            logger.error(f"Error handling feedback event: {e}")
    
    def _handle_adjustment_event(self, adjustment: Dict[str, Any]):
        """Handle adjustment events from the feedback loop"""
        try:
            # Inform threshold adjustment about parameter changes
            self._inform_threshold_adjustment_about_changes(adjustment)
            
            # Update pattern learning with adjustment information
            self._update_pattern_learning_with_adjustment(adjustment)
            
        except Exception as e:
            logger.error(f"Error handling adjustment event: {e}")
    
    def _handle_weight_optimization(self, optimization_result: Dict[str, Any]):
        """Handle weight optimization from adaptive weights"""
        try:
            # Update feedback loop with weight changes
            self._update_feedback_loop_with_weight_changes(optimization_result)
            
            # Update pattern learning with weight information
            self._update_pattern_learning_with_weights(optimization_result)
            
            # Update component correlations
            self._update_component_correlations('weights', optimization_result)
            
        except Exception as e:
            logger.error(f"Error handling weight optimization: {e}")
    
    def _handle_pattern_discovery(self, pattern: SuccessPattern):
        """Handle pattern discovery from pattern learning"""
        try:
            # Update adaptive weights with pattern information
            self._update_adaptive_weights_with_pattern(pattern)
            
            # Update threshold adjustment with pattern insights
            self._update_threshold_adjustment_with_pattern(pattern)
            
            # Update feedback loop with pattern information
            self._update_feedback_loop_with_pattern(pattern)
            
        except Exception as e:
            logger.error(f"Error handling pattern discovery: {e}")
    
    def _handle_pattern_prediction(self, prediction: PatternPrediction):
        """Handle pattern predictions from pattern learning"""
        try:
            # Use prediction to inform other components
            self._inform_components_about_prediction(prediction)
            
        except Exception as e:
            logger.error(f"Error handling pattern prediction: {e}")
    
    def _handle_threshold_optimization(self, optimization_result: OptimizationResult):
        """Handle threshold optimization results"""
        try:
            # Update feedback loop with threshold changes
            self._update_feedback_loop_with_threshold_changes(optimization_result)
            
            # Update adaptive weights with threshold information
            self._update_adaptive_weights_with_thresholds(optimization_result)
            
            # Update component correlations
            self._update_component_correlations('thresholds', optimization_result)
            
        except Exception as e:
            logger.error(f"Error handling threshold optimization: {e}")
    
    def _handle_threshold_update(self, threshold_config):
        """Handle threshold configuration updates"""
        try:
            # Inform other components about threshold changes
            self._inform_components_about_threshold_changes(threshold_config)
            
        except Exception as e:
            logger.error(f"Error handling threshold update: {e}")
    
    def _inform_adaptive_weights_about_performance(self, pair_id: str, success: bool):
        """Inform adaptive weights about performance outcomes"""
        try:
            # Find recent selections for this pair
            recent_selections = [
                result for result in self.adaptive_weights.selection_history
                if result.pair_id == pair_id and result.actual_performance is None
            ]
            
            # Update performance feedback
            for selection in recent_selections[:1]:  # Update most recent
                performance_value = 0.02 if success else -0.01  # Simplified performance
                self.adaptive_weights.add_performance_feedback(pair_id, performance_value)
                break
            
        except Exception as e:
            logger.error(f"Error informing adaptive weights: {e}")
    
    def _update_pattern_learning_with_feedback(self, event: FeedbackEvent):
        """Update pattern learning with feedback information"""
        try:
            # Create training sample from feedback
            pair_data = {
                'pair_id': event.pair_id,
                'market_regime': event.market_conditions.get('regime', 'NORMAL'),
                'correlation': 0.7,  # Would get actual values
                'volatility1': 0.2,
                'volatility2': 0.2,
                'spread_history': [0.0] * 50  # Would get actual spread history
            }
            
            success = event.signal.value in ['POSITIVE', 'STRONG_POSITIVE']
            self.pattern_learning.add_training_sample(pair_data, success)
            
        except Exception as e:
            logger.error(f"Error updating pattern learning with feedback: {e}")
    
    def _update_threshold_adjustment_with_feedback(self, event: FeedbackEvent):
        """Update threshold adjustment with feedback information"""
        try:
            # Convert feedback to performance metrics
            performance_metrics = {
                'sharpe_ratio': 0.8 if event.signal.value in ['POSITIVE', 'STRONG_POSITIVE'] else 0.2,
                'max_drawdown': 0.05 if event.signal.value in ['POSITIVE', 'STRONG_POSITIVE'] else 0.15,
                'win_rate': 0.6 if event.signal.value in ['POSITIVE', 'STRONG_POSITIVE'] else 0.4
            }
            
            self.threshold_adjustment.add_performance_data(performance_metrics)
            
        except Exception as e:
            logger.error(f"Error updating threshold adjustment with feedback: {e}")
    
    def _update_component_correlations(self, component: str, event_data: Any):
        """Update correlations between components"""
        try:
            # Simplified correlation update
            # In practice, this would involve more sophisticated correlation analysis
            
            if component == 'feedback':
                self.component_correlations['feedback_weights'] += 0.01
                self.component_correlations['feedback_patterns'] += 0.01
                self.component_correlations['feedback_thresholds'] += 0.01
            elif component == 'weights':
                self.component_correlations['weights_patterns'] += 0.01
                self.component_correlations['weights_thresholds'] += 0.01
            elif component == 'thresholds':
                self.component_correlations['patterns_thresholds'] += 0.01
            
            # Normalize correlations
            for key in self.component_correlations:
                self.component_correlations[key] = min(1.0, self.component_correlations[key])
            
        except Exception as e:
            logger.error(f"Error updating component correlations: {e}")
    
    def add_integrated_performance_data(self, pair_id: str, trade_data: Dict[str, Any]):
        """Add performance data to all components"""
        try:
            # Create performance record for feedback loop
            performance_record = PerformanceRecord(
                pair_id=pair_id,
                timestamp=datetime.now(),
                sharpe_ratio=trade_data.get('sharpe_ratio', 0.0),
                max_drawdown=trade_data.get('max_drawdown', 0.0),
                win_rate=trade_data.get('win_rate', 0.5),
                profit_factor=trade_data.get('profit_factor', 1.0),
                total_return=trade_data.get('total_return', 0.0),
                volatility=trade_data.get('volatility', 0.1),
                num_trades=trade_data.get('num_trades', 1),
                avg_trade_duration=trade_data.get('avg_trade_duration', 60.0),
                avg_profit_per_trade=trade_data.get('avg_profit_per_trade', 0.001),
                market_regime=trade_data.get('market_regime', 'NORMAL'),
                volatility_regime=trade_data.get('volatility_regime', 'NORMAL'),
                correlation_level=trade_data.get('correlation_level', 0.7),
                strategy_params=trade_data.get('strategy_params', {}),
                attribution_factors=trade_data.get('attribution_factors', {})
            )
            
            # Add to feedback loop
            self.feedback_loop.add_performance_record(performance_record)
            
            # Add to adaptive weights (if it's a selection result)
            if 'selection_score' in trade_data:
                performance_value = trade_data.get('total_return', 0.0)
                self.adaptive_weights.add_performance_feedback(pair_id, performance_value)
            
            # Add to pattern learning
            success = trade_data.get('total_return', 0.0) > 0
            self.pattern_learning.add_training_sample(trade_data, success)
            
            # Add to threshold adjustment
            performance_metrics = {
                'sharpe_ratio': trade_data.get('sharpe_ratio', 0.0),
                'max_drawdown': trade_data.get('max_drawdown', 0.0),
                'win_rate': trade_data.get('win_rate', 0.5),
                'profit_factor': trade_data.get('profit_factor', 1.0)
            }
            self.threshold_adjustment.add_performance_data(performance_metrics, trade_data)
            
            # Update integrated metrics
            self._update_integrated_metrics()
            
        except Exception as e:
            logger.error(f"Error adding integrated performance data: {e}")
    
    def get_integrated_pair_recommendation(self, pair_data: Dict[str, Any]) -> IntegratedRecommendation:
        """Get integrated recommendation for a pair"""
        try:
            # Get recommendations from each component
            feedback_recommendations = self._get_feedback_recommendations(pair_data)
            weight_recommendations = self._get_weight_recommendations(pair_data)
            pattern_recommendations = self._get_pattern_recommendations(pair_data)
            threshold_recommendations = self._get_threshold_recommendations(pair_data)
            
            # Integrate recommendations
            final_recommendation, confidence = self._integrate_recommendations(
                feedback_recommendations, weight_recommendations,
                pattern_recommendations, threshold_recommendations
            )
            
            # Create integrated recommendation
            integrated_rec = IntegratedRecommendation(
                recommendation_id=f"integrated_{pair_data.get('pair_id', 'unknown')}_{int(datetime.now().timestamp())}",
                pair_id=pair_data.get('pair_id', 'unknown'),
                timestamp=datetime.now(),
                feedback_recommendations=feedback_recommendations,
                weight_recommendations=weight_recommendations,
                pattern_recommendations=pattern_recommendations,
                threshold_recommendations=threshold_recommendations,
                final_recommendation=final_recommendation,
                confidence=confidence,
                expected_impact=self._calculate_expected_impact(final_recommendation),
                priority=self._determine_priority(final_recommendation, confidence),
                implementation_complexity=self._assess_implementation_complexity(final_recommendation),
                expected_implementation_time=self._estimate_implementation_time(final_recommendation)
            )
            
            # Store recommendation
            self.integrated_recommendations.append(integrated_rec)
            
            # Trigger callbacks
            for callback in self.recommendation_callbacks:
                try:
                    callback(integrated_rec)
                except Exception as e:
                    logger.error(f"Error in recommendation callback: {e}")
            
            return integrated_rec
            
        except Exception as e:
            logger.error(f"Error getting integrated recommendation: {e}")
            return self._create_default_recommendation(pair_data.get('pair_id', 'unknown'))
    
    def _get_feedback_recommendations(self, pair_data: Dict[str, Any]) -> List[str]:
        """Get recommendations from feedback loop"""
        try:
            pair_id = pair_data.get('pair_id', 'unknown')
            current_performance = {
                'sharpe_ratio': pair_data.get('sharpe_ratio', 0.0),
                'max_drawdown': pair_data.get('max_drawdown', 0.0),
                'win_rate': pair_data.get('win_rate', 0.5)
            }
            
            return self.feedback_loop.get_adjustment_recommendations(pair_id, current_performance)
            
        except Exception as e:
            logger.error(f"Error getting feedback recommendations: {e}")
            return []
    
    def _get_weight_recommendations(self, pair_data: Dict[str, Any]) -> List[str]:
        """Get recommendations from adaptive weights"""
        try:
            # Calculate pair score
            result = self.adaptive_weights.calculate_pair_score(pair_data)
            
            # Generate recommendations based on score
            recommendations = []
            if result.overall_score > 0.8:
                recommendations.append("HIGH_PRIORITY_PAIR")
            elif result.overall_score > 0.6:
                recommendations.append("MEDIUM_PRIORITY_PAIR")
            else:
                recommendations.append("LOW_PRIORITY_PAIR")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting weight recommendations: {e}")
            return []
    
    def _get_pattern_recommendations(self, pair_data: Dict[str, Any]) -> List[str]:
        """Get recommendations from pattern learning"""
        try:
            # Get pattern prediction
            prediction = self.pattern_learning.predict_success(pair_data)
            
            # Generate recommendations based on prediction
            recommendations = []
            if prediction.success_probability > 0.8:
                recommendations.append("HIGH_SUCCESS_PROBABILITY")
            elif prediction.success_probability > 0.6:
                recommendations.append("MODERATE_SUCCESS_PROBABILITY")
            else:
                recommendations.append("LOW_SUCCESS_PROBABILITY")
            
            if prediction.confidence.value in ['HIGH', 'VERY_HIGH']:
                recommendations.append("HIGH_CONFIDENCE_PREDICTION")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting pattern recommendations: {e}")
            return []
    
    def _get_threshold_recommendations(self, pair_data: Dict[str, Any]) -> List[str]:
        """Get recommendations from threshold adjustment"""
        try:
            # Get current thresholds
            current_thresholds = self.threshold_adjustment.get_current_thresholds()
            
            # Generate recommendations based on thresholds
            recommendations = []
            
            correlation_threshold = current_thresholds.get(ThresholdType.CORRELATION_THRESHOLD, 0.7)
            if pair_data.get('correlation', 0.0) > correlation_threshold:
                recommendations.append("MEETS_CORRELATION_THRESHOLD")
            else:
                recommendations.append("BELOW_CORRELATION_THRESHOLD")
            
            entry_threshold = current_thresholds.get(ThresholdType.ENTRY_THRESHOLD, 2.0)
            if abs(pair_data.get('spread_zscore', 0.0)) > entry_threshold:
                recommendations.append("MEETS_ENTRY_THRESHOLD")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting threshold recommendations: {e}")
            return []
    
    def _integrate_recommendations(self, feedback_recs: List[str], weight_recs: List[str],
                                 pattern_recs: List[str], threshold_recs: List[str]) -> Tuple[str, float]:
        """Integrate recommendations from all components"""
        try:
            # Score different recommendation types
            recommendation_scores = {}
            
            # Process feedback recommendations
            for rec in feedback_recs:
                if 'REDUCE' in rec or 'DECREASE' in rec:
                    recommendation_scores['REDUCE_EXPOSURE'] = recommendation_scores.get('REDUCE_EXPOSURE', 0) + 1
                elif 'INCREASE' in rec or 'MONITOR' in rec:
                    recommendation_scores['INCREASE_MONITORING'] = recommendation_scores.get('INCREASE_MONITORING', 0) + 1
            
            # Process weight recommendations
            for rec in weight_recs:
                if 'HIGH_PRIORITY' in rec:
                    recommendation_scores['TRADE_PAIR'] = recommendation_scores.get('TRADE_PAIR', 0) + 2
                elif 'MEDIUM_PRIORITY' in rec:
                    recommendation_scores['TRADE_PAIR'] = recommendation_scores.get('TRADE_PAIR', 0) + 1
                elif 'LOW_PRIORITY' in rec:
                    recommendation_scores['AVOID_PAIR'] = recommendation_scores.get('AVOID_PAIR', 0) + 1
            
            # Process pattern recommendations
            for rec in pattern_recs:
                if 'HIGH_SUCCESS' in rec:
                    recommendation_scores['TRADE_PAIR'] = recommendation_scores.get('TRADE_PAIR', 0) + 2
                elif 'LOW_SUCCESS' in rec:
                    recommendation_scores['AVOID_PAIR'] = recommendation_scores.get('AVOID_PAIR', 0) + 1
            
            # Process threshold recommendations
            for rec in threshold_recs:
                if 'MEETS' in rec:
                    recommendation_scores['TRADE_PAIR'] = recommendation_scores.get('TRADE_PAIR', 0) + 1
                elif 'BELOW' in rec:
                    recommendation_scores['AVOID_PAIR'] = recommendation_scores.get('AVOID_PAIR', 0) + 1
            
            # Determine final recommendation
            if not recommendation_scores:
                return "MONITOR_CLOSELY", 0.5
            
            final_recommendation = max(recommendation_scores.items(), key=lambda x: x[1])[0]
            max_score = max(recommendation_scores.values())
            total_score = sum(recommendation_scores.values())
            
            confidence = max_score / total_score if total_score > 0 else 0.5
            
            return final_recommendation, confidence
            
        except Exception as e:
            logger.error(f"Error integrating recommendations: {e}")
            return "MONITOR_CLOSELY", 0.5
    
    def _calculate_expected_impact(self, recommendation: str) -> float:
        """Calculate expected impact of recommendation"""
        impact_map = {
            'TRADE_PAIR': 0.02,
            'AVOID_PAIR': -0.01,
            'REDUCE_EXPOSURE': 0.005,
            'INCREASE_MONITORING': 0.001,
            'MONITOR_CLOSELY': 0.0
        }
        return impact_map.get(recommendation, 0.0)
    
    def _determine_priority(self, recommendation: str, confidence: float) -> str:
        """Determine priority of recommendation"""
        if confidence > 0.8:
            return "HIGH"
        elif confidence > 0.6:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_implementation_complexity(self, recommendation: str) -> str:
        """Assess implementation complexity"""
        complexity_map = {
            'TRADE_PAIR': "LOW",
            'AVOID_PAIR': "LOW",
            'REDUCE_EXPOSURE': "MEDIUM",
            'INCREASE_MONITORING': "LOW",
            'MONITOR_CLOSELY': "LOW"
        }
        return complexity_map.get(recommendation, "MEDIUM")
    
    def _estimate_implementation_time(self, recommendation: str) -> timedelta:
        """Estimate implementation time"""
        time_map = {
            'TRADE_PAIR': timedelta(minutes=1),
            'AVOID_PAIR': timedelta(seconds=1),
            'REDUCE_EXPOSURE': timedelta(minutes=5),
            'INCREASE_MONITORING': timedelta(minutes=2),
            'MONITOR_CLOSELY': timedelta(seconds=30)
        }
        return time_map.get(recommendation, timedelta(minutes=1))
    
    def _create_default_recommendation(self, pair_id: str) -> IntegratedRecommendation:
        """Create default recommendation"""
        return IntegratedRecommendation(
            recommendation_id=f"default_{pair_id}_{int(datetime.now().timestamp())}",
            pair_id=pair_id,
            timestamp=datetime.now(),
            feedback_recommendations=[],
            weight_recommendations=[],
            pattern_recommendations=[],
            threshold_recommendations=[],
            final_recommendation="MONITOR_CLOSELY",
            confidence=0.5,
            expected_impact=0.0,
            priority="LOW",
            implementation_complexity="LOW",
            expected_implementation_time=timedelta(minutes=1)
        )
    
    def _update_integrated_metrics(self):
        """Update integrated performance metrics"""
        try:
            # Get metrics from each component
            feedback_summary = self.feedback_loop.get_feedback_summary()
            weights_summary = self.adaptive_weights.get_system_summary()
            patterns_summary = self.pattern_learning.get_learning_summary()
            thresholds_summary = self.threshold_adjustment.get_system_summary()
            
            # Calculate integrated metrics
            integrated_metrics = IntegratedPerformanceMetrics(
                timestamp=datetime.now(),
                system_sharpe_ratio=weights_summary.get('avg_performance', 0.0),
                system_max_drawdown=0.1,  # Would calculate from actual data
                system_win_rate=0.6,     # Would calculate from actual data
                system_profit_factor=1.2, # Would calculate from actual data
                feedback_loop_effectiveness=feedback_summary.get('adjustment_effectiveness', 0.0),
                weight_adaptation_score=weights_summary.get('optimization_success_rate', 0.0),
                pattern_learning_accuracy=patterns_summary.get('model_performance', {}).get('ensemble', {}).get('cv_score_mean', 0.0),
                threshold_optimization_score=thresholds_summary.get('optimization_success_rate', 0.0),
                component_synchronization=self._calculate_component_synchronization(),
                learning_convergence=self._calculate_learning_convergence(),
                adaptation_speed=self._calculate_adaptation_speed(),
                market_regime=self.adaptive_weights.current_regime.value,
                volatility_regime='NORMAL',  # Would get from actual data
                learning_phase=self.learning_phase,
                learning_progress=self.learning_progress
            )
            
            # Store metrics
            self.integrated_metrics.append(integrated_metrics)
            
            # Keep only recent metrics
            if len(self.integrated_metrics) > 1000:
                self.integrated_metrics = self.integrated_metrics[-1000:]
            
            # Update learning progress
            self._update_learning_progress()
            
            # Trigger callbacks
            for callback in self.integration_callbacks:
                try:
                    callback(integrated_metrics)
                except Exception as e:
                    logger.error(f"Error in integration callback: {e}")
            
        except Exception as e:
            logger.error(f"Error updating integrated metrics: {e}")
    
    def _calculate_component_synchronization(self) -> float:
        """Calculate synchronization between components"""
        try:
            # Simple synchronization metric based on component correlations
            avg_correlation = np.mean(list(self.component_correlations.values()))
            return min(1.0, max(0.0, avg_correlation))
        except Exception as e:
            logger.error(f"Error calculating component synchronization: {e}")
            return 0.5
    
    def _calculate_learning_convergence(self) -> float:
        """Calculate learning convergence"""
        try:
            # Based on stability of recent performance
            if len(self.integrated_metrics) < 10:
                return 0.0
            
            recent_sharpe_ratios = [m.system_sharpe_ratio for m in self.integrated_metrics[-10:]]
            convergence = 1.0 - (np.std(recent_sharpe_ratios) / (np.mean(recent_sharpe_ratios) + 1e-6))
            return min(1.0, max(0.0, convergence))
            
        except Exception as e:
            logger.error(f"Error calculating learning convergence: {e}")
            return 0.5
    
    def _calculate_adaptation_speed(self) -> float:
        """Calculate adaptation speed"""
        try:
            # Based on how quickly the system responds to changes
            # Simplified implementation
            return 0.7  # Would implement actual calculation
        except Exception as e:
            logger.error(f"Error calculating adaptation speed: {e}")
            return 0.5
    
    def _update_learning_progress(self):
        """Update learning progress and phase"""
        try:
            # Update learning progress based on metrics
            if len(self.integrated_metrics) >= 100:
                recent_metrics = self.integrated_metrics[-100:]
                avg_performance = np.mean([m.system_sharpe_ratio for m in recent_metrics])
                
                if avg_performance > 1.5:
                    self.learning_phase = LearningPhase.MASTERY
                    self.learning_progress = 1.0
                elif avg_performance > 1.0:
                    self.learning_phase = LearningPhase.REFINEMENT
                    self.learning_progress = 0.8
                elif avg_performance > 0.5:
                    self.learning_phase = LearningPhase.EXPLOITATION
                    self.learning_progress = 0.6
                elif len(self.integrated_metrics) > 50:
                    self.learning_phase = LearningPhase.EXPLORATION
                    self.learning_progress = 0.4
                else:
                    self.learning_phase = LearningPhase.BOOTSTRAP
                    self.learning_progress = 0.2
            
        except Exception as e:
            logger.error(f"Error updating learning progress: {e}")
    
    def start_integrated_system(self):
        """Start all integrated components"""
        try:
            # Start individual components
            self.feedback_loop.start_feedback_loop()
            self.adaptive_weights.start_optimization_loop()
            self.pattern_learning.start_learning_loop()
            self.threshold_adjustment.start_monitoring()
            
            # Start integration thread
            self.integration_thread = threading.Thread(target=self._integration_loop, daemon=True)
            self.integration_thread.start()
            
            self.system_status = IntegrationStatus.RUNNING
            logger.info("Phase 3 integrated system started")
            
        except Exception as e:
            logger.error(f"Error starting integrated system: {e}")
            self.system_status = IntegrationStatus.ERROR
    
    def stop_integrated_system(self):
        """Stop all integrated components"""
        try:
            # Stop integration thread
            self.stop_event.set()
            if self.integration_thread:
                self.integration_thread.join(timeout=10)
            
            # Stop individual components
            self.feedback_loop.stop_feedback_loop()
            self.adaptive_weights.stop_optimization_loop()
            self.pattern_learning.stop_learning_loop()
            self.threshold_adjustment.stop_monitoring()
            
            self.system_status = IntegrationStatus.STOPPED
            logger.info("Phase 3 integrated system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping integrated system: {e}")
    
    def _integration_loop(self):
        """Main integration loop"""
        while not self.stop_event.is_set():
            try:
                # Update integrated metrics
                self._update_integrated_metrics()
                
                # Check for cross-component optimizations
                self._check_cross_component_optimizations()
                
                # Update learning synergies
                self._update_learning_synergies()
                
                # Clean up old data
                self._cleanup_old_data()
                
                # Sleep
                self.stop_event.wait(60)  # 1 minute
                
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                time.sleep(60)
    
    def _check_cross_component_optimizations(self):
        """Check for cross-component optimization opportunities"""
        try:
            # Check if components are working in synergy
            if self.component_correlations['weights_patterns'] > 0.8:
                # High correlation between weights and patterns
                self.learning_synergies['weight_pattern_synergy'] = 0.9
            
            if self.component_correlations['feedback_thresholds'] > 0.8:
                # High correlation between feedback and thresholds
                self.learning_synergies['threshold_feedback_synergy'] = 0.9
            
            # Check for global optimization opportunities
            if all(synergy > 0.7 for synergy in self.learning_synergies.values()):
                self.learning_synergies['global_optimization'] = 0.95
                self.system_status = IntegrationStatus.OPTIMIZING
            
        except Exception as e:
            logger.error(f"Error checking cross-component optimizations: {e}")
    
    def _update_learning_synergies(self):
        """Update learning synergies between components"""
        try:
            # Update based on component performance
            feedback_effectiveness = self.feedback_loop.get_feedback_summary().get('adjustment_effectiveness', 0.0)
            self.learning_synergies['feedback_adaptation'] = feedback_effectiveness
            
            # Normalize synergies
            for key in self.learning_synergies:
                self.learning_synergies[key] = min(1.0, max(0.0, self.learning_synergies[key]))
            
        except Exception as e:
            logger.error(f"Error updating learning synergies: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data from all components"""
        try:
            # Clean up integrated recommendations
            cutoff_time = datetime.now() - timedelta(days=30)
            self.integrated_recommendations = [
                rec for rec in self.integrated_recommendations
                if rec.timestamp > cutoff_time
            ]
            
            # Clean up integrated metrics
            if len(self.integrated_metrics) > 1000:
                self.integrated_metrics = self.integrated_metrics[-1000:]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_integrated_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive integrated system summary"""
        try:
            # Get summaries from all components
            feedback_summary = self.feedback_loop.get_feedback_summary()
            weights_summary = self.adaptive_weights.get_system_summary()
            patterns_summary = self.pattern_learning.get_learning_summary()
            thresholds_summary = self.threshold_adjustment.get_system_summary()
            
            # Calculate integrated statistics
            recent_metrics = self.integrated_metrics[-100:] if len(self.integrated_metrics) >= 100 else self.integrated_metrics
            
            return {
                'system_status': self.system_status.value,
                'learning_phase': self.learning_phase.value,
                'learning_progress': self.learning_progress,
                'component_summaries': {
                    'feedback_loop': feedback_summary,
                    'adaptive_weights': weights_summary,
                    'pattern_learning': patterns_summary,
                    'threshold_adjustment': thresholds_summary
                },
                'integrated_metrics': {
                    'avg_system_sharpe': np.mean([m.system_sharpe_ratio for m in recent_metrics]) if recent_metrics else 0.0,
                    'avg_component_sync': np.mean([m.component_synchronization for m in recent_metrics]) if recent_metrics else 0.0,
                    'avg_learning_convergence': np.mean([m.learning_convergence for m in recent_metrics]) if recent_metrics else 0.0,
                    'avg_adaptation_speed': np.mean([m.adaptation_speed for m in recent_metrics]) if recent_metrics else 0.0
                },
                'component_correlations': self.component_correlations,
                'learning_synergies': self.learning_synergies,
                'recent_recommendations': len([r for r in self.integrated_recommendations if r.timestamp > datetime.now() - timedelta(days=7)]),
                'system_health': self._assess_system_health(),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating integrated system summary: {e}")
            return {}
    
    def _assess_system_health(self) -> str:
        """Assess overall system health"""
        try:
            health_score = 0
            
            # Check component health
            if self.system_status == IntegrationStatus.RUNNING:
                health_score += 25
            
            # Check learning progress
            if self.learning_progress > 0.7:
                health_score += 25
            
            # Check component synchronization
            avg_sync = np.mean(list(self.component_correlations.values()))
            if avg_sync > 0.6:
                health_score += 25
            
            # Check learning synergies
            avg_synergy = np.mean(list(self.learning_synergies.values()))
            if avg_synergy > 0.6:
                health_score += 25
            
            if health_score >= 75:
                return "EXCELLENT"
            elif health_score >= 50:
                return "GOOD"
            elif health_score >= 25:
                return "FAIR"
            else:
                return "POOR"
                
        except Exception as e:
            logger.error(f"Error assessing system health: {e}")
            return "UNKNOWN"
    
    def add_integration_callback(self, callback: Callable[[IntegratedPerformanceMetrics], None]):
        """Add callback for integration events"""
        self.integration_callbacks.append(callback)
    
    def add_recommendation_callback(self, callback: Callable[[IntegratedRecommendation], None]):
        """Add callback for recommendation events"""
        self.recommendation_callbacks.append(callback)

# Example usage
if __name__ == "__main__":
    # Create integrated system
    integrated_system = Phase3IntegratedSystem()
    
    # Add callbacks
    def integration_handler(metrics: IntegratedPerformanceMetrics):
        print(f"INTEGRATION UPDATE: Sharpe={metrics.system_sharpe_ratio:.3f}, Learning={metrics.learning_progress:.1%}")
    
    def recommendation_handler(recommendation: IntegratedRecommendation):
        print(f"RECOMMENDATION: {recommendation.pair_id} - {recommendation.final_recommendation} (Confidence: {recommendation.confidence:.1%})")
    
    integrated_system.add_integration_callback(integration_handler)
    integrated_system.add_recommendation_callback(recommendation_handler)
    
    # Start integrated system
    integrated_system.start_integrated_system()
    
    # Simulate trading data
    import random
    
    for i in range(50):
        # Simulate pair data
        pair_data = {
            'pair_id': f"PAIR_{i}",
            'symbol1': f"STOCK_{i}A",
            'symbol2': f"STOCK_{i}B",
            'correlation': random.uniform(0.5, 0.9),
            'volatility1': random.uniform(0.1, 0.3),
            'volatility2': random.uniform(0.1, 0.3),
            'spread_zscore': random.gauss(0, 1),
            'market_regime': random.choice(['TRENDING', 'MEAN_REVERTING', 'HIGH_VOLATILITY']),
            'sharpe_ratio': random.gauss(0.8, 0.3),
            'max_drawdown': random.uniform(0.05, 0.15),
            'win_rate': random.uniform(0.45, 0.65),
            'profit_factor': random.uniform(0.9, 1.4),
            'total_return': random.gauss(0.02, 0.03),
            'volatility': random.uniform(0.1, 0.25),
            'num_trades': random.randint(10, 50),
            'avg_trade_duration': random.uniform(30, 180),
            'avg_profit_per_trade': random.gauss(0.001, 0.002)
        }
        
        # Add performance data
        integrated_system.add_integrated_performance_data(pair_data['pair_id'], pair_data)
        
        # Get recommendation
        recommendation = integrated_system.get_integrated_pair_recommendation(pair_data)
        
        # Simulate some delay
        time.sleep(0.1)
    
    # Get system summary
    summary = integrated_system.get_integrated_system_summary()
    print("\nIntegrated System Summary:")
    print(json.dumps(summary, indent=2))
    
    # Stop integrated system
    integrated_system.stop_integrated_system() 