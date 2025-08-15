"""
Performance Adaptation - Template-Category-Aware Performance Monitoring
======================================================================

Performance-based strategy adaptation with template categories and inheritance awareness.
Monitors performance degradation and triggers appropriate adaptations.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque

from strategy_templates.base import TemplateRegistry, TemplateCategory


class PerformanceDegradationLevel(Enum):
    """Levels of performance degradation"""
    NONE = "none"
    MINOR = "minor"          # 5-10% degradation
    MODERATE = "moderate"    # 10-20% degradation
    MAJOR = "major"          # 20-35% degradation
    CRITICAL = "critical"    # >35% degradation


class PerformanceThreshold(Enum):
    """Performance threshold types"""
    ABSOLUTE = "absolute"    # Absolute performance values
    RELATIVE = "relative"    # Relative to baseline
    ROLLING = "rolling"      # Rolling window comparison
    BENCHMARK = "benchmark"  # Comparison to benchmark


@dataclass
class PerformanceAdaptationConfig:
    """Configuration for performance adaptation"""
    # Degradation thresholds by template category
    degradation_thresholds: Dict[TemplateCategory, Dict[PerformanceDegradationLevel, float]] = field(
        default_factory=lambda: {
            TemplateCategory.BASE: {
                PerformanceDegradationLevel.MINOR: 0.05,
                PerformanceDegradationLevel.MODERATE: 0.10,
                PerformanceDegradationLevel.MAJOR: 0.20,
                PerformanceDegradationLevel.CRITICAL: 0.35
            },
            TemplateCategory.SPECIFIC: {
                PerformanceDegradationLevel.MINOR: 0.08,
                PerformanceDegradationLevel.MODERATE: 0.15,
                PerformanceDegradationLevel.MAJOR: 0.25,
                PerformanceDegradationLevel.CRITICAL: 0.40
            },
            TemplateCategory.COMPOSITE: {
                PerformanceDegradationLevel.MINOR: 0.10,
                PerformanceDegradationLevel.MODERATE: 0.18,
                PerformanceDegradationLevel.MAJOR: 0.30,
                PerformanceDegradationLevel.CRITICAL: 0.45
            }
        }
    )
    
    # Performance metrics weights
    metric_weights: Dict[str, float] = field(default_factory=lambda: {
        'total_return': 0.25,
        'sharpe_ratio': 0.20,
        'max_drawdown': 0.20,
        'win_rate': 0.15,
        'profit_factor': 0.10,
        'volatility': 0.10
    })
    
    # Monitoring windows
    baseline_window: int = 50    # Number of periods for baseline
    monitoring_window: int = 20  # Number of periods for current performance
    lookback_periods: int = 100  # Total periods to keep in history
    
    # Adaptation triggers
    consecutive_poor_periods: int = 3  # Trigger after N consecutive poor periods
    min_sample_size: int = 10         # Minimum samples before triggering
    confidence_level: float = 0.95    # Statistical confidence level


class PerformanceAdaptation:
    """
    Performance-based strategy adaptation with template categories
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[PerformanceAdaptationConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or PerformanceAdaptationConfig()
        
        # Performance tracking
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.lookback_periods))
        self.baseline_metrics: Dict[str, float] = {}
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        
        # Degradation tracking
        self.consecutive_poor_count = 0
        self.last_degradation_level = PerformanceDegradationLevel.NONE
        self.degradation_history: List[Tuple[datetime, PerformanceDegradationLevel]] = []
        
        self.logger.info("Performance Adaptation initialized")
    
    def initialize_for_template(self, template_id: str):
        """Initialize performance tracking for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            
            # Reset tracking
            self.performance_history.clear()
            self.baseline_metrics.clear()
            self.consecutive_poor_count = 0
            self.last_degradation_level = PerformanceDegradationLevel.NONE
            
            self.logger.info(f"Performance tracking initialized for template {template_id} (category: {self.current_template_category.value})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize performance tracking: {e}")
            raise
    
    def update_performance_metrics(self, metrics: Dict[str, float]) -> bool:
        """
        Update performance metrics and check for degradation
        Returns True if adaptation is recommended
        """
        try:
            if not self.current_template_id:
                self.logger.warning("No template initialized for performance tracking")
                return False
            
            # Store metrics with timestamp
            timestamp = datetime.now()
            
            for metric_name, value in metrics.items():
                if metric_name in self.config.metric_weights:
                    self.performance_history[metric_name].append((timestamp, value))
            
            # Update baseline if we have enough data
            if self._should_update_baseline():
                self._update_baseline_metrics()
            
            # Check for performance degradation
            degradation_level = self._assess_performance_degradation()
            
            # Update degradation tracking
            if degradation_level != PerformanceDegradationLevel.NONE:
                self.consecutive_poor_count += 1
                self.degradation_history.append((timestamp, degradation_level))
            else:
                self.consecutive_poor_count = 0
            
            self.last_degradation_level = degradation_level
            
            # Determine if adaptation is needed
            adaptation_needed = self._should_trigger_adaptation(degradation_level)
            
            if adaptation_needed:
                self.logger.info(f"Performance adaptation recommended: {degradation_level.value} degradation detected")
            
            return adaptation_needed
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
            return False
    
    def get_performance_analysis(self) -> Dict[str, Any]:
        """Get comprehensive performance analysis"""
        if not self.current_template_id:
            return {}
        
        try:
            current_metrics = self._calculate_current_metrics()
            degradation_analysis = self._analyze_degradation_patterns()
            recommendations = self._generate_performance_recommendations()
            
            return {
                'template_id': self.current_template_id,
                'template_category': self.current_template_category.value,
                'current_degradation_level': self.last_degradation_level.value,
                'consecutive_poor_periods': self.consecutive_poor_count,
                'baseline_metrics': self.baseline_metrics.copy(),
                'current_metrics': current_metrics,
                'degradation_analysis': degradation_analysis,
                'recommendations': recommendations,
                'performance_trend': self._calculate_performance_trend(),
                'risk_assessment': self._assess_performance_risk()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating performance analysis: {e}")
            return {'error': str(e)}
    
    def get_adaptation_parameters(self, degradation_level: PerformanceDegradationLevel) -> Dict[str, float]:
        """Get recommended parameter adjustments based on degradation level"""
        if not self.current_template_category:
            return {}
        
        # Base adaptation factors by degradation level
        adaptation_factors = {
            PerformanceDegradationLevel.MINOR: 0.05,     # 5% adjustment
            PerformanceDegradationLevel.MODERATE: 0.15,  # 15% adjustment
            PerformanceDegradationLevel.MAJOR: 0.30,     # 30% adjustment
            PerformanceDegradationLevel.CRITICAL: 0.50   # 50% adjustment
        }
        
        base_factor = adaptation_factors.get(degradation_level, 0.0)
        
        # Category-specific adjustments
        category_multipliers = {
            TemplateCategory.BASE: 0.8,      # More conservative
            TemplateCategory.SPECIFIC: 1.0,  # Standard
            TemplateCategory.COMPOSITE: 1.2  # More aggressive
        }
        
        adjustment_factor = base_factor * category_multipliers[self.current_template_category]
        
        # Generate parameter recommendations
        return {
            'signal_threshold_adjustment': adjustment_factor * 0.5,  # Increase selectivity
            'position_size_reduction': adjustment_factor * 0.3,     # Reduce position sizes
            'stop_loss_tightening': adjustment_factor * 0.2,        # Tighten stop losses
            'risk_reduction_factor': adjustment_factor,             # Overall risk reduction
            'confidence_threshold_increase': adjustment_factor * 0.4 # Increase confidence requirements
        }
    
    # Private helper methods
    def _should_update_baseline(self) -> bool:
        """Check if baseline should be updated"""
        # Update baseline if we have enough data and current performance is stable
        min_data_points = max(metric_history for metric_history in self.performance_history.values() 
                             if len(metric_history) > 0)
        
        return (len(min_data_points) >= self.config.baseline_window and 
                not self.baseline_metrics and
                self.consecutive_poor_count < 2)  # Only update during stable periods
    
    def _update_baseline_metrics(self):
        """Update baseline performance metrics"""
        try:
            for metric_name, weight in self.config.metric_weights.items():
                if metric_name in self.performance_history:
                    history = self.performance_history[metric_name]
                    if len(history) >= self.config.baseline_window:
                        # Use the first baseline_window periods for baseline
                        baseline_values = [value for _, value in list(history)[:self.config.baseline_window]]
                        self.baseline_metrics[metric_name] = np.mean(baseline_values)
            
            self.logger.info("Baseline metrics updated")
            
        except Exception as e:
            self.logger.error(f"Error updating baseline metrics: {e}")
    
    def _assess_performance_degradation(self) -> PerformanceDegradationLevel:
        """Assess current level of performance degradation"""
        if not self.baseline_metrics or not self.current_template_category:
            return PerformanceDegradationLevel.NONE
        
        try:
            current_metrics = self._calculate_current_metrics()
            
            # Calculate weighted degradation score
            total_degradation = 0.0
            total_weight = 0.0
            
            for metric_name, baseline_value in self.baseline_metrics.items():
                if metric_name in current_metrics and metric_name in self.config.metric_weights:
                    current_value = current_metrics[metric_name]
                    weight = self.config.metric_weights[metric_name]
                    
                    # Calculate degradation (handling different metric types)
                    degradation = self._calculate_metric_degradation(metric_name, baseline_value, current_value)
                    
                    total_degradation += degradation * weight
                    total_weight += weight
            
            if total_weight == 0:
                return PerformanceDegradationLevel.NONE
            
            average_degradation = total_degradation / total_weight
            
            # Map degradation to level based on template category thresholds
            thresholds = self.config.degradation_thresholds[self.current_template_category]
            
            if average_degradation >= thresholds[PerformanceDegradationLevel.CRITICAL]:
                return PerformanceDegradationLevel.CRITICAL
            elif average_degradation >= thresholds[PerformanceDegradationLevel.MAJOR]:
                return PerformanceDegradationLevel.MAJOR
            elif average_degradation >= thresholds[PerformanceDegradationLevel.MODERATE]:
                return PerformanceDegradationLevel.MODERATE
            elif average_degradation >= thresholds[PerformanceDegradationLevel.MINOR]:
                return PerformanceDegradationLevel.MINOR
            else:
                return PerformanceDegradationLevel.NONE
                
        except Exception as e:
            self.logger.error(f"Error assessing performance degradation: {e}")
            return PerformanceDegradationLevel.NONE
    
    def _calculate_metric_degradation(self, metric_name: str, baseline_value: float, current_value: float) -> float:
        """Calculate degradation for a specific metric"""
        if baseline_value == 0:
            return 0.0
        
        # Handle different metric types
        if metric_name in ['total_return', 'sharpe_ratio', 'win_rate', 'profit_factor']:
            # Higher is better - degradation when current < baseline
            degradation = max(0, (baseline_value - current_value) / abs(baseline_value))
        elif metric_name in ['max_drawdown', 'volatility']:
            # Lower is better - degradation when current > baseline
            degradation = max(0, (current_value - baseline_value) / abs(baseline_value))
        else:
            # Default: higher is better
            degradation = max(0, (baseline_value - current_value) / abs(baseline_value))
        
        return degradation
    
    def _calculate_current_metrics(self) -> Dict[str, float]:
        """Calculate current performance metrics from recent data"""
        current_metrics = {}
        
        for metric_name in self.config.metric_weights.keys():
            if metric_name in self.performance_history:
                history = self.performance_history[metric_name]
                if len(history) >= self.config.monitoring_window:
                    # Use recent monitoring_window periods
                    recent_values = [value for _, value in list(history)[-self.config.monitoring_window:]]
                    current_metrics[metric_name] = np.mean(recent_values)
        
        return current_metrics
    
    def _should_trigger_adaptation(self, degradation_level: PerformanceDegradationLevel) -> bool:
        """Determine if adaptation should be triggered"""
        # No adaptation for no degradation
        if degradation_level == PerformanceDegradationLevel.NONE:
            return False
        
        # Immediate adaptation for critical degradation
        if degradation_level == PerformanceDegradationLevel.CRITICAL:
            return True
        
        # For other levels, check consecutive poor periods
        if self.consecutive_poor_count >= self.config.consecutive_poor_periods:
            return True
        
        # Check if we have minimum sample size
        min_samples = min(len(history) for history in self.performance_history.values() 
                         if len(history) > 0)
        
        return min_samples >= self.config.min_sample_size
    
    def _analyze_degradation_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in performance degradation"""
        if not self.degradation_history:
            return {'pattern': 'no_degradation', 'trend': 'stable'}
        
        recent_degradations = self.degradation_history[-10:]  # Last 10 degradation events
        
        # Analyze frequency
        if len(self.degradation_history) > 1:
            time_diffs = [(d2[0] - d1[0]).total_seconds() / 3600 for d1, d2 in 
                         zip(self.degradation_history[:-1], self.degradation_history[1:])]
            avg_frequency = np.mean(time_diffs) if time_diffs else 0
        else:
            avg_frequency = 0
        
        # Analyze severity trend
        severity_levels = [d[1] for d in recent_degradations]
        severity_values = [
            {'none': 0, 'minor': 1, 'moderate': 2, 'major': 3, 'critical': 4}[level.value] 
            for level in severity_levels
        ]
        
        if len(severity_values) > 1:
            severity_trend = np.polyfit(range(len(severity_values)), severity_values, 1)[0]
        else:
            severity_trend = 0
        
        return {
            'degradation_frequency_hours': avg_frequency,
            'recent_degradation_count': len(recent_degradations),
            'severity_trend': 'increasing' if severity_trend > 0.1 else 'decreasing' if severity_trend < -0.1 else 'stable',
            'most_common_level': max(set(severity_levels), key=severity_levels.count).value if severity_levels else 'none'
        }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate specific performance improvement recommendations"""
        recommendations = []
        
        if self.last_degradation_level == PerformanceDegradationLevel.NONE:
            recommendations.append("Performance is stable - maintain current parameters")
            return recommendations
        
        current_metrics = self._calculate_current_metrics()
        
        # Analyze specific metrics for targeted recommendations
        for metric_name, current_value in current_metrics.items():
            if metric_name in self.baseline_metrics:
                baseline_value = self.baseline_metrics[metric_name]
                degradation = self._calculate_metric_degradation(metric_name, baseline_value, current_value)
                
                if degradation > 0.1:  # 10% degradation threshold
                    if metric_name == 'sharpe_ratio':
                        recommendations.append("Consider reducing position sizes to improve risk-adjusted returns")
                    elif metric_name == 'max_drawdown':
                        recommendations.append("Implement tighter stop-losses to control drawdowns")
                    elif metric_name == 'win_rate':
                        recommendations.append("Increase signal selectivity to improve win rate")
                    elif metric_name == 'volatility':
                        recommendations.append("Reduce position sizes to lower portfolio volatility")
        
        # General recommendations based on degradation level
        if self.last_degradation_level in [PerformanceDegradationLevel.MAJOR, PerformanceDegradationLevel.CRITICAL]:
            recommendations.extend([
                "Consider temporary reduction in overall risk exposure",
                "Review strategy assumptions and market conditions",
                "Implement more conservative parameter settings"
            ])
        
        return recommendations
    
    def _calculate_performance_trend(self) -> str:
        """Calculate overall performance trend"""
        if not self.performance_history.get('total_return'):
            return 'insufficient_data'
        
        returns_history = self.performance_history['total_return']
        if len(returns_history) < 10:
            return 'insufficient_data'
        
        recent_returns = [value for _, value in list(returns_history)[-10:]]
        
        # Simple trend analysis
        if len(recent_returns) > 1:
            trend_slope = np.polyfit(range(len(recent_returns)), recent_returns, 1)[0]
            
            if trend_slope > 0.01:
                return 'improving'
            elif trend_slope < -0.01:
                return 'declining'
            else:
                return 'stable'
        
        return 'stable'
    
    def _assess_performance_risk(self) -> str:
        """Assess current performance risk level"""
        risk_factors = 0
        
        # Check consecutive poor performance
        if self.consecutive_poor_count >= 3:
            risk_factors += 2
        elif self.consecutive_poor_count >= 2:
            risk_factors += 1
        
        # Check degradation level
        if self.last_degradation_level == PerformanceDegradationLevel.CRITICAL:
            risk_factors += 3
        elif self.last_degradation_level == PerformanceDegradationLevel.MAJOR:
            risk_factors += 2
        elif self.last_degradation_level == PerformanceDegradationLevel.MODERATE:
            risk_factors += 1
        
        # Check degradation frequency
        if len(self.degradation_history) > 5:  # More than 5 degradation events
            recent_degradations = [d for d in self.degradation_history 
                                 if (datetime.now() - d[0]).days <= 7]  # In last week
            if len(recent_degradations) > 2:
                risk_factors += 2
        
        # Map risk factors to risk level
        if risk_factors >= 5:
            return 'high'
        elif risk_factors >= 3:
            return 'medium'
        elif risk_factors >= 1:
            return 'low'
        else:
            return 'minimal'
