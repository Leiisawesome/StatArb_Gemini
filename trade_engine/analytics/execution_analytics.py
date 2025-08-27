"""
Execution Analytics System

Integrates analytics with execution engine to provide:
- Execution quality tracking and analysis
- Performance attribution for execution costs
- Real-time execution monitoring
- Execution optimization recommendations
- Historical execution analysis
- Algorithm performance comparison

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from abc import ABC, abstractmethod

# Import execution engine components
from core_structure.execution_engine.execution_engine import (
    ExecutionEngine, ExecutionResult, ExecutionStatus, 
    ExecutionAlgorithm, ExecutionMetrics
)

# Import performance analytics components
from .legacy_performance_analytics import PerformanceAnalyzer, AttributionAnalyzer

logger = logging.getLogger(__name__)


class ExecutionQualityLevel(Enum):
    """Execution quality levels"""
    EXCELLENT = "excellent"      # Quality score >= 0.9
    GOOD = "good"               # Quality score >= 0.7
    AVERAGE = "average"         # Quality score >= 0.5
    POOR = "poor"               # Quality score >= 0.3
    VERY_POOR = "very_poor"     # Quality score < 0.3


class ExecutionCostType(Enum):
    """Types of execution costs"""
    COMMISSION = "commission"
    SLIPPAGE = "slippage"
    MARKET_IMPACT = "market_impact"
    TIMING_COST = "timing_cost"
    OPPORTUNITY_COST = "opportunity_cost"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"


@dataclass
class ExecutionAnalyticsConfig:
    """
    Configuration for Execution Analytics
    
    Controls the behavior of execution analytics including:
    - Quality thresholds and scoring weights
    - Performance tracking parameters
    - Alert and monitoring settings
    - Analysis frequency and retention
    """
    
    # Quality scoring weights (must sum to 1.0)
    fill_rate_weight: float = 0.25
    implementation_shortfall_weight: float = 0.30
    market_impact_weight: float = 0.20
    timing_cost_weight: float = 0.15
    execution_time_weight: float = 0.10
    
    # Quality thresholds
    excellent_threshold: float = 0.9
    good_threshold: float = 0.7
    average_threshold: float = 0.5
    poor_threshold: float = 0.3
    
    # Performance tracking
    max_history_size: int = 10000
    retention_days: int = 365
    analysis_frequency_minutes: int = 5
    
    # Alert thresholds
    high_cost_alert_threshold: float = 0.005  # 50 bps
    poor_quality_alert_threshold: float = 0.5
    execution_time_alert_threshold: float = 300  # 5 minutes
    
    # Analysis settings
    enable_real_time_analysis: bool = True
    enable_historical_analysis: bool = True
    enable_algorithm_comparison: bool = True
    enable_venue_analysis: bool = True
    
    # Reporting settings
    default_report_period: str = "daily"
    enable_automated_reports: bool = True
    report_retention_days: int = 90
    
    def __post_init__(self):
        """Validate configuration"""
        total_weight = (self.fill_rate_weight + self.implementation_shortfall_weight + 
                       self.market_impact_weight + self.timing_cost_weight + 
                       self.execution_time_weight)
        
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Quality scoring weights must sum to 1.0, got {total_weight}")
        
        if not (0 <= self.excellent_threshold <= 1):
            raise ValueError(f"Excellent threshold must be between 0 and 1, got {self.excellent_threshold}")
        
        if not (0 <= self.good_threshold <= 1):
            raise ValueError(f"Good threshold must be between 0 and 1, got {self.good_threshold}")
        
        if not (0 <= self.average_threshold <= 1):
            raise ValueError(f"Average threshold must be between 0 and 1, got {self.average_threshold}")
        
        if not (0 <= self.poor_threshold <= 1):
            raise ValueError(f"Poor threshold must be between 0 and 1, got {self.poor_threshold}")


@dataclass
class ExecutionQualityMetrics:
    """
    Detailed execution quality metrics
    
    Provides comprehensive metrics for evaluating execution quality
    across multiple dimensions including fill rates, costs, timing, and impact.
    """
    
    # Basic execution metrics
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: str = ""
    algorithm: ExecutionAlgorithm = ExecutionAlgorithm.MARKET
    
    # Fill metrics
    requested_quantity: float = 0.0
    executed_quantity: float = 0.0
    fill_rate: float = 0.0
    partial_fills: int = 0
    
    # Price metrics
    target_price: float = 0.0
    average_price: float = 0.0
    price_improvement: float = 0.0
    price_disimprovement: float = 0.0
    
    # Cost metrics
    total_cost: float = 0.0
    commission_cost: float = 0.0
    slippage_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    implementation_shortfall: float = 0.0
    
    # Timing metrics
    execution_time: float = 0.0
    time_to_first_fill: float = 0.0
    time_to_completion: float = 0.0
    
    # Market conditions
    market_volatility: float = 0.0
    market_volume: float = 0.0
    spread_at_execution: float = 0.0
    
    # Quality scores (0-1 scale)
    fill_rate_score: float = 0.0
    implementation_shortfall_score: float = 0.0
    market_impact_score: float = 0.0
    timing_cost_score: float = 0.0
    execution_time_score: float = 0.0
    
    # Overall quality
    overall_quality_score: float = 0.0
    quality_level: ExecutionQualityLevel = ExecutionQualityLevel.AVERAGE
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    venue: str = ""
    strategy_id: str = ""
    user_id: str = ""
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.requested_quantity > 0:
            self.fill_rate = (self.executed_quantity / self.requested_quantity) * 100
        
        if self.target_price > 0 and self.average_price > 0:
            if self.side.upper() == "BUY":
                self.price_improvement = max(0, self.target_price - self.average_price)
                self.price_disimprovement = max(0, self.average_price - self.target_price)
            else:  # SELL
                self.price_improvement = max(0, self.average_price - self.target_price)
                self.price_disimprovement = max(0, self.target_price - self.average_price)


@dataclass
class ExecutionQualityReport:
    """
    Comprehensive execution quality report
    
    Provides detailed analysis of execution quality including:
    - Individual execution quality metrics
    - Aggregate performance statistics
    - Quality trends and patterns
    - Recommendations for improvement
    """
    
    # Report metadata
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    report_type: str = "execution_quality"
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    generated_at: datetime = field(default_factory=datetime.now)
    
    # Summary statistics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    success_rate: float = 0.0
    
    # Quality distribution
    excellent_executions: int = 0
    good_executions: int = 0
    average_executions: int = 0
    poor_executions: int = 0
    very_poor_executions: int = 0
    
    # Average metrics
    avg_fill_rate: float = 0.0
    avg_implementation_shortfall: float = 0.0
    avg_market_impact: float = 0.0
    avg_timing_cost: float = 0.0
    avg_execution_time: float = 0.0
    avg_quality_score: float = 0.0
    
    # Cost analysis
    total_execution_cost: float = 0.0
    avg_execution_cost: float = 0.0
    cost_by_type: Dict[ExecutionCostType, float] = field(default_factory=dict)
    
    # Algorithm performance
    algorithm_performance: Dict[ExecutionAlgorithm, Dict[str, float]] = field(default_factory=dict)
    
    # Venue performance
    venue_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Quality trends
    quality_trend: str = "stable"  # improving, declining, stable
    quality_volatility: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    improvement_opportunities: List[str] = field(default_factory=list)
    
    # Detailed metrics
    quality_metrics: List[ExecutionQualityMetrics] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived statistics"""
        # Note: success_rate and quality distribution percentages are calculated
        # in _calculate_report_statistics after the counts are set


@dataclass
class ExecutionAttributionReport:
    """
    Execution cost attribution report
    
    Provides detailed breakdown of execution costs and their attribution
    to different factors including market conditions, algorithm choice,
    timing, and venue selection.
    """
    
    # Report metadata
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    
    # Total costs
    total_execution_cost: float = 0.0
    total_volume: float = 0.0
    cost_per_share: float = 0.0
    cost_basis_points: float = 0.0
    
    # Cost breakdown by type
    commission_cost: float = 0.0
    slippage_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    
    # Attribution by factor
    market_condition_attribution: float = 0.0
    algorithm_attribution: float = 0.0
    timing_attribution: float = 0.0
    venue_attribution: float = 0.0
    size_attribution: float = 0.0
    
    # Factor analysis
    volatility_impact: float = 0.0
    volume_impact: float = 0.0
    spread_impact: float = 0.0
    urgency_impact: float = 0.0
    
    # Benchmark comparison
    benchmark_cost: float = 0.0
    cost_savings: float = 0.0
    cost_efficiency: float = 0.0
    
    # Recommendations
    cost_optimization_opportunities: List[str] = field(default_factory=list)
    expected_savings: float = 0.0


class ExecutionAnalytics:
    """
    Execution Analytics System
    
    Integrates analytics with execution engine to provide:
    - Real-time execution quality tracking
    - Performance attribution for execution costs
    - Execution optimization recommendations
    - Historical execution analysis
    - Algorithm performance comparison
    - Venue performance analysis
    """
    
    def __init__(self, 
                 execution_engine: ExecutionEngine,
                 performance_analyzer: PerformanceAnalyzer,
                 config: Optional[ExecutionAnalyticsConfig] = None):
        """
        Initialize Execution Analytics
        
        Args:
            execution_engine: Core execution engine
            performance_analyzer: Performance analytics module
            config: Execution analytics configuration
        """
        self.execution_engine = execution_engine
        self.performance_analyzer = performance_analyzer
        self.config = config or ExecutionAnalyticsConfig()
        
        # Initialize attribution analyzer
        self.attribution_analyzer = AttributionAnalyzer()
        
        # Execution tracking
        self.execution_history: List[ExecutionResult] = []
        self.quality_metrics: List[ExecutionQualityMetrics] = []
        self.quality_reports: List[ExecutionQualityReport] = []
        
        # Performance tracking
        self.performance_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'avg_quality_score': 0.0,
            'avg_fill_rate': 0.0,
            'avg_implementation_shortfall': 0.0,
            'total_execution_cost': 0.0
        }
        
        # Real-time monitoring
        self.real_time_alerts: List[Dict[str, Any]] = []
        self.quality_trends: List[Dict[str, Any]] = []
        
        logger.info("ExecutionAnalytics initialized successfully")
    
    async def track_execution(self, execution_result: ExecutionResult) -> ExecutionQualityMetrics:
        """
        Track execution and calculate quality metrics
        
        Args:
            execution_result: Result from execution engine
            
        Returns:
            Execution quality metrics
        """
        try:
            # Create quality metrics
            quality_metrics = ExecutionQualityMetrics(
                execution_id=execution_result.request_id,
                symbol=execution_result.symbol,
                side=execution_result.side.name,  # Use .name to get 'BUY' instead of 'OrderSide.BUY'
                algorithm=execution_result.algorithm_used,
                requested_quantity=execution_result.requested_quantity,
                executed_quantity=execution_result.executed_quantity,
                average_price=execution_result.average_price,
                total_cost=execution_result.total_cost,
                implementation_shortfall=execution_result.implementation_shortfall,
                market_impact_cost=execution_result.market_impact,
                timing_cost=execution_result.timing_cost,
                execution_time=execution_result.execution_time
            )
            
            # Copy timestamp from execution result if it exists
            if hasattr(execution_result, 'timestamp') and execution_result.timestamp:
                quality_metrics.timestamp = execution_result.timestamp
            
            # Calculate quality metrics
            await self._calculate_quality_metrics(quality_metrics, execution_result)
            
            # Store metrics
            self.quality_metrics.append(quality_metrics)
            self.execution_history.append(execution_result)
            
            # Update performance metrics
            self._update_performance_metrics(quality_metrics)
            
            # Check for alerts
            await self._check_alerts(quality_metrics)
            
            logger.info(f"Execution tracked: {execution_result.request_id}, "
                       f"Quality Score: {quality_metrics.overall_quality_score:.3f}")
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error tracking execution: {e}")
            raise
    
    async def _calculate_quality_metrics(self, metrics: ExecutionQualityMetrics, 
                                       execution_result: ExecutionResult):
        """
        Calculate comprehensive quality metrics for execution
        
        Args:
            metrics: Execution quality metrics to populate
            execution_result: Original execution result for additional data
        """
        try:
            # Calculate basic derived metrics
            self._calculate_basic_metrics(metrics, execution_result)
            
            # Calculate market condition metrics
            await self._calculate_market_condition_metrics(metrics, execution_result)
            
            # Calculate timing metrics
            self._calculate_timing_metrics(metrics, execution_result)
            
            # Calculate cost breakdown
            self._calculate_cost_breakdown(metrics, execution_result)
            
            # Calculate quality scores
            await self._calculate_quality_scores(metrics)
            
            # Calculate additional quality indicators
            self._calculate_quality_indicators(metrics)
            
            logger.debug(f"Quality metrics calculated for {metrics.execution_id}")
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {e}")
            raise
    
    def _calculate_basic_metrics(self, metrics: ExecutionQualityMetrics, 
                               execution_result: ExecutionResult):
        """
        Calculate basic execution metrics
        
        Args:
            metrics: Execution quality metrics to populate
            execution_result: Original execution result
        """
        try:
            # Fill rate calculation
            if metrics.requested_quantity > 0:
                metrics.fill_rate = (metrics.executed_quantity / metrics.requested_quantity) * 100
            
            # Partial fills calculation
            if hasattr(execution_result, 'orders') and execution_result.orders:
                metrics.partial_fills = len([order for order in execution_result.orders 
                                          if order.filled_quantity > 0])
            
            # Price improvement/disimprovement calculation
            if hasattr(execution_result, 'target_price') and execution_result.target_price:
                metrics.target_price = execution_result.target_price
                if metrics.target_price > 0 and metrics.average_price > 0:
                    if metrics.side.upper() == "BUY":
                        metrics.price_improvement = max(0, metrics.target_price - metrics.average_price)
                        metrics.price_disimprovement = max(0, metrics.average_price - metrics.target_price)
                    else:  # SELL
                        metrics.price_improvement = max(0, metrics.average_price - metrics.target_price)
                        metrics.price_disimprovement = max(0, metrics.target_price - metrics.average_price)
            
        except Exception as e:
            logger.error(f"Error calculating basic metrics: {e}")
            raise
    
    async def _calculate_market_condition_metrics(self, metrics: ExecutionQualityMetrics,
                                                execution_result: ExecutionResult):
        """
        Calculate market condition metrics
        
        Args:
            metrics: Execution quality metrics to populate
            execution_result: Original execution result
        """
        try:
            # Get market data from execution engine if available
            if hasattr(self.execution_engine, 'get_market_conditions'):
                try:
                    market_conditions = await self.execution_engine.get_market_conditions(metrics.symbol)
                    if market_conditions:
                        metrics.market_volatility = getattr(market_conditions, 'volatility', 0.0)
                        metrics.market_volume = getattr(market_conditions, 'volume', 0.0)
                        metrics.spread_at_execution = getattr(market_conditions, 'spread', 0.0)
                except Exception as e:
                    logger.warning(f"Could not get market conditions for {metrics.symbol}: {e}")
            
            # Fallback: estimate market conditions from execution data
            if metrics.market_volatility == 0.0 and metrics.implementation_shortfall != 0.0:
                # Estimate volatility from implementation shortfall
                metrics.market_volatility = abs(metrics.implementation_shortfall) * 10  # Rough estimate
            
            if metrics.market_volume == 0.0 and metrics.executed_quantity > 0:
                # Estimate volume from executed quantity
                metrics.market_volume = metrics.executed_quantity * 100  # Rough estimate
            
        except Exception as e:
            logger.error(f"Error calculating market condition metrics: {e}")
            raise
    
    def _calculate_timing_metrics(self, metrics: ExecutionQualityMetrics,
                                execution_result: ExecutionResult):
        """
        Calculate timing-related metrics
        
        Args:
            metrics: Execution quality metrics to populate
            execution_result: Original execution result
        """
        try:
            # Time to first fill
            if hasattr(execution_result, 'orders') and execution_result.orders:
                filled_orders = [order for order in execution_result.orders 
                               if order.filled_quantity > 0 and hasattr(order, 'fill_time')]
                if filled_orders:
                    first_fill_time = min(order.fill_time for order in filled_orders 
                                        if hasattr(order, 'fill_time'))
                    if hasattr(execution_result, 'timestamp'):
                        metrics.time_to_first_fill = (first_fill_time - execution_result.timestamp).total_seconds()
            
            # Time to completion
            if hasattr(execution_result, 'timestamp') and hasattr(execution_result, 'completion_time'):
                metrics.time_to_completion = (execution_result.completion_time - execution_result.timestamp).total_seconds()
            else:
                # Fallback: use execution_time if available
                metrics.time_to_completion = metrics.execution_time
            
        except Exception as e:
            logger.error(f"Error calculating timing metrics: {e}")
            raise
    
    def _calculate_cost_breakdown(self, metrics: ExecutionQualityMetrics,
                                execution_result: ExecutionResult):
        """
        Calculate detailed cost breakdown
        
        Args:
            metrics: Execution quality metrics to populate
            execution_result: Original execution result
        """
        try:
            # Commission cost (if available in execution result)
            if hasattr(execution_result, 'commission_cost'):
                metrics.commission_cost = execution_result.commission_cost
            else:
                # Estimate commission cost (typical 5 bps)
                commission_rate = 0.0005
                metrics.commission_cost = metrics.executed_quantity * metrics.average_price * commission_rate
            
            # Slippage cost (difference between expected and actual price)
            if metrics.target_price > 0 and metrics.average_price > 0:
                price_diff = abs(metrics.average_price - metrics.target_price)
                metrics.slippage_cost = price_diff * metrics.executed_quantity
            
            # Market impact cost (already set from execution result)
            # Timing cost (already set from execution result)
            # Implementation shortfall (already set from execution result)
            
            # Validate total cost
            calculated_total = (metrics.commission_cost + metrics.slippage_cost + 
                              metrics.market_impact_cost + metrics.timing_cost)
            
            if abs(calculated_total - metrics.total_cost) > 0.01:  # Allow small difference
                logger.warning(f"Cost breakdown doesn't match total cost: "
                             f"calculated={calculated_total:.4f}, total={metrics.total_cost:.4f}")
            
        except Exception as e:
            logger.error(f"Error calculating cost breakdown: {e}")
            raise
    
    def _calculate_quality_indicators(self, metrics: ExecutionQualityMetrics):
        """
        Calculate additional quality indicators
        
        Args:
            metrics: Execution quality metrics to populate
        """
        try:
            # Efficiency ratio (executed quantity / requested quantity)
            if metrics.requested_quantity > 0:
                efficiency_ratio = metrics.executed_quantity / metrics.requested_quantity
            else:
                efficiency_ratio = 0.0
            
            # Cost efficiency (cost per share)
            if metrics.executed_quantity > 0:
                cost_per_share = metrics.total_cost / metrics.executed_quantity
            else:
                cost_per_share = 0.0
            
            # Speed efficiency (execution time vs expected time)
            expected_time = 60  # 1 minute expected
            if metrics.execution_time > 0:
                speed_efficiency = min(1.0, expected_time / metrics.execution_time)
            else:
                speed_efficiency = 1.0
            
            # Store additional indicators in metadata
            if not hasattr(metrics, 'additional_indicators'):
                metrics.additional_indicators = {}
            
            metrics.additional_indicators.update({
                'efficiency_ratio': efficiency_ratio,
                'cost_per_share': cost_per_share,
                'speed_efficiency': speed_efficiency,
                'fill_completeness': metrics.fill_rate / 100.0,
                'price_efficiency': 1.0 - min(1.0, abs(metrics.implementation_shortfall) / 0.01)
            })
            
        except Exception as e:
            logger.error(f"Error calculating quality indicators: {e}")
            raise
    
    async def _calculate_quality_scores(self, metrics: ExecutionQualityMetrics):
        """
        Calculate quality scores for execution metrics
        
        Args:
            metrics: Execution quality metrics to score
        """
        try:
            # Calculate individual quality scores using normalize_metric
            metrics.fill_rate_score = self._normalize_metric(
                metrics.fill_rate, 0.0, 100.0, higher_is_better=True
            )
            
            metrics.implementation_shortfall_score = self._normalize_metric(
                abs(metrics.implementation_shortfall), 0.0, 0.01, higher_is_better=False
            )
            
            metrics.market_impact_score = self._normalize_metric(
                abs(metrics.market_impact_cost), 0.0, 0.005, higher_is_better=False
            )
            
            metrics.timing_cost_score = self._normalize_metric(
                abs(metrics.timing_cost), 0.0, 0.003, higher_is_better=False
            )
            
            metrics.execution_time_score = self._normalize_metric(
                metrics.execution_time, 0.0, 300.0, higher_is_better=False
            )
            
            # Calculate overall quality score
            metrics.overall_quality_score = self._calculate_quality_score(metrics)
            
            # Determine quality level
            if metrics.overall_quality_score >= self.config.excellent_threshold:
                metrics.quality_level = ExecutionQualityLevel.EXCELLENT
            elif metrics.overall_quality_score >= self.config.good_threshold:
                metrics.quality_level = ExecutionQualityLevel.GOOD
            elif metrics.overall_quality_score >= self.config.average_threshold:
                metrics.quality_level = ExecutionQualityLevel.AVERAGE
            elif metrics.overall_quality_score >= self.config.poor_threshold:
                metrics.quality_level = ExecutionQualityLevel.POOR
            else:
                metrics.quality_level = ExecutionQualityLevel.VERY_POOR
                
        except Exception as e:
            logger.error(f"Error calculating quality scores: {e}")
            raise
    
    def _calculate_quality_score(self, metrics: ExecutionQualityMetrics) -> float:
        """
        Calculate overall quality score from individual component scores
        
        Args:
            metrics: Execution quality metrics with individual scores
            
        Returns:
            Overall quality score (0-1 scale)
        """
        try:
            # Weighted combination of individual quality scores
            overall_score = (
                metrics.fill_rate_score * self.config.fill_rate_weight +
                metrics.implementation_shortfall_score * self.config.implementation_shortfall_weight +
                metrics.market_impact_score * self.config.market_impact_weight +
                metrics.timing_cost_score * self.config.timing_cost_weight +
                metrics.execution_time_score * self.config.execution_time_weight
            )
            
            # Ensure score is within valid range
            overall_score = max(0.0, min(1.0, overall_score))
            
            logger.debug(f"Calculated overall quality score: {overall_score:.3f}")
            return overall_score
            
        except Exception as e:
            logger.error(f"Error calculating overall quality score: {e}")
            return 0.0
    
    def _normalize_metric(self, value: float, min_val: float, max_val: float, 
                        higher_is_better: bool = True) -> float:
        """
        Normalize a metric value to 0-1 scale
        
        Args:
            value: Raw metric value
            min_val: Minimum expected value
            max_val: Maximum expected value
            higher_is_better: Whether higher values are better (True) or worse (False)
            
        Returns:
            Normalized score (0-1 scale)
        """
        try:
            # Handle edge cases
            if max_val == min_val:
                return 0.5  # Neutral score for zero range
            
            if value < min_val:
                value = min_val
            elif value > max_val:
                value = max_val
            
            # Normalize to 0-1 scale
            normalized = (value - min_val) / (max_val - min_val)
            
            # Invert if lower values are better
            if not higher_is_better:
                normalized = 1.0 - normalized
            
            # Ensure result is within valid range
            normalized = max(0.0, min(1.0, normalized))
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing metric: {e}")
            return 0.5  # Neutral score on error
    
    def _calculate_adaptive_quality_score(self, metrics: ExecutionQualityMetrics, 
                                       historical_data: List[ExecutionQualityMetrics]) -> float:
        """
        Calculate adaptive quality score based on historical performance
        
        Args:
            metrics: Current execution quality metrics
            historical_data: Historical execution data for comparison
            
        Returns:
            Adaptive quality score (0-1 scale)
        """
        try:
            if not historical_data:
                # Fall back to standard quality score if no historical data
                return self._calculate_quality_score(metrics)
            
            # Calculate percentile-based scores
            fill_rate_percentile = self._calculate_percentile_score(
                metrics.fill_rate, [m.fill_rate for m in historical_data], higher_is_better=True
            )
            
            shortfall_percentile = self._calculate_percentile_score(
                abs(metrics.implementation_shortfall), 
                [abs(m.implementation_shortfall) for m in historical_data], 
                higher_is_better=False
            )
            
            impact_percentile = self._calculate_percentile_score(
                abs(metrics.market_impact_cost), 
                [abs(m.market_impact_cost) for m in historical_data], 
                higher_is_better=False
            )
            
            time_percentile = self._calculate_percentile_score(
                metrics.execution_time, 
                [m.execution_time for m in historical_data], 
                higher_is_better=False
            )
            
            # Calculate adaptive overall score
            adaptive_score = (
                fill_rate_percentile * self.config.fill_rate_weight +
                shortfall_percentile * self.config.implementation_shortfall_weight +
                impact_percentile * self.config.market_impact_weight +
                time_percentile * self.config.execution_time_weight
            )
            
            return max(0.0, min(1.0, adaptive_score))
            
        except Exception as e:
            logger.error(f"Error calculating adaptive quality score: {e}")
            return self._calculate_quality_score(metrics)
    
    def _calculate_percentile_score(self, value: float, historical_values: List[float], 
                                  higher_is_better: bool = True) -> float:
        """
        Calculate percentile-based score relative to historical data
        
        Args:
            value: Current value
            historical_values: Historical values for comparison
            higher_is_better: Whether higher values are better
            
        Returns:
            Percentile score (0-1 scale)
        """
        try:
            if not historical_values:
                return 0.5  # Neutral score if no historical data
            
            # Calculate percentile
            sorted_values = sorted(historical_values)
            percentile = 0.0
            
            for i, hist_value in enumerate(sorted_values):
                if value <= hist_value:
                    percentile = i / len(sorted_values)
                    break
            else:
                percentile = 1.0
            
            # Invert if lower values are better
            if not higher_is_better:
                percentile = 1.0 - percentile
            
            return percentile
            
        except Exception as e:
            logger.error(f"Error calculating percentile score: {e}")
            return 0.5
    
    def _calculate_risk_adjusted_quality_score(self, metrics: ExecutionQualityMetrics) -> float:
        """
        Calculate risk-adjusted quality score considering market conditions
        
        Args:
            metrics: Execution quality metrics
            
        Returns:
            Risk-adjusted quality score (0-1 scale)
        """
        try:
            # Base quality score
            base_score = self._calculate_quality_score(metrics)
            
            # Risk adjustment factors
            volatility_adjustment = 1.0
            volume_adjustment = 1.0
            spread_adjustment = 1.0
            
            # Adjust for market volatility
            if metrics.market_volatility > 0:
                # Higher volatility should not penalize as much
                volatility_adjustment = min(1.2, 1.0 + (metrics.market_volatility * 10))
            
            # Adjust for market volume
            if metrics.market_volume > 0:
                # Higher volume should not penalize as much
                volume_adjustment = min(1.1, 1.0 + (metrics.market_volume / 1000000))
            
            # Adjust for spread
            if metrics.spread_at_execution > 0:
                # Higher spread should not penalize as much
                spread_adjustment = min(1.15, 1.0 + (metrics.spread_at_execution * 100))
            
            # Calculate risk-adjusted score
            risk_adjusted_score = base_score * volatility_adjustment * volume_adjustment * spread_adjustment
            
            # Ensure score is within valid range
            risk_adjusted_score = max(0.0, min(1.0, risk_adjusted_score))
            
            return risk_adjusted_score
            
        except Exception as e:
            logger.error(f"Error calculating risk-adjusted quality score: {e}")
            return self._calculate_quality_score(metrics)
    
    def _update_performance_metrics(self, metrics: ExecutionQualityMetrics):
        """
        Update aggregate performance metrics
        
        Args:
            metrics: New execution quality metrics
        """
        try:
            self.performance_metrics['total_executions'] += 1
            
            if metrics.fill_rate >= 95:  # Consider successful if 95%+ filled
                self.performance_metrics['successful_executions'] += 1
            
            # Update averages using exponential moving average
            alpha = 0.1  # Smoothing factor
            self.performance_metrics['avg_quality_score'] = (
                (1 - alpha) * self.performance_metrics['avg_quality_score'] +
                alpha * metrics.overall_quality_score
            )
            
            self.performance_metrics['avg_fill_rate'] = (
                (1 - alpha) * self.performance_metrics['avg_fill_rate'] +
                alpha * metrics.fill_rate
            )
            
            self.performance_metrics['avg_implementation_shortfall'] = (
                (1 - alpha) * self.performance_metrics['avg_implementation_shortfall'] +
                alpha * abs(metrics.implementation_shortfall)
            )
            
            self.performance_metrics['total_execution_cost'] += metrics.total_cost
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def _check_alerts(self, metrics: ExecutionQualityMetrics):
        """
        Check for alert conditions
        
        Args:
            metrics: Execution quality metrics to check
        """
        try:
            alerts = []
            
            # High cost alert
            if abs(metrics.implementation_shortfall) > self.config.high_cost_alert_threshold:
                alerts.append({
                    'type': 'high_cost',
                    'execution_id': metrics.execution_id,
                    'symbol': metrics.symbol,
                    'cost': metrics.implementation_shortfall,
                    'threshold': self.config.high_cost_alert_threshold,
                    'timestamp': datetime.now()
                })
            
            # Poor quality alert
            if metrics.overall_quality_score < self.config.poor_quality_alert_threshold:
                alerts.append({
                    'type': 'poor_quality',
                    'execution_id': metrics.execution_id,
                    'symbol': metrics.symbol,
                    'quality_score': metrics.overall_quality_score,
                    'threshold': self.config.poor_quality_alert_threshold,
                    'timestamp': datetime.now()
                })
            
            # Execution time alert
            if metrics.execution_time > self.config.execution_time_alert_threshold:
                alerts.append({
                    'type': 'slow_execution',
                    'execution_id': metrics.execution_id,
                    'symbol': metrics.symbol,
                    'execution_time': metrics.execution_time,
                    'threshold': self.config.execution_time_alert_threshold,
                    'timestamp': datetime.now()
                })
            
            # Store alerts
            self.real_time_alerts.extend(alerts)
            
            # Log alerts
            for alert in alerts:
                logger.warning(f"Execution Alert: {alert['type']} for {alert['symbol']}")
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def generate_quality_report(self, 
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None,
                                    symbol: Optional[str] = None,
                                    algorithm: Optional[ExecutionAlgorithm] = None) -> ExecutionQualityReport:
        """
        Generate execution quality report
        
        Args:
            start_time: Report start time
            end_time: Report end time
            symbol: Filter by symbol
            algorithm: Filter by algorithm
            
        Returns:
            Execution quality report
        """
        try:
            # Set default time range
            if end_time is None:
                end_time = datetime.now()
            if start_time is None:
                start_time = end_time - timedelta(days=1)
            
            # Filter metrics
            filtered_metrics = [
                m for m in self.quality_metrics
                if start_time <= m.timestamp <= end_time
                and (symbol is None or m.symbol == symbol)
                and (algorithm is None or m.algorithm == algorithm)
            ]
            
            if not filtered_metrics:
                logger.warning("No execution metrics found for report period")
                return ExecutionQualityReport()
            
            # Create report
            report = ExecutionQualityReport(
                period_start=start_time,
                period_end=end_time,
                total_executions=len(filtered_metrics),
                quality_metrics=filtered_metrics
            )
            
            # Calculate statistics
            await self._calculate_report_statistics(report, filtered_metrics)
            
            # Generate recommendations
            await self._generate_recommendations(report, filtered_metrics)
            
            # Store report
            self.quality_reports.append(report)
            
            logger.info(f"Quality report generated: {report.report_id}, "
                       f"Period: {start_time} to {end_time}, "
                       f"Executions: {report.total_executions}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            raise
    
    async def _calculate_report_statistics(self, report: ExecutionQualityReport, 
                                         metrics: List[ExecutionQualityMetrics]):
        """
        Calculate statistics for quality report
        
        Args:
            report: Report to populate
            metrics: List of quality metrics
        """
        try:
            # Basic counts
            report.successful_executions = sum(1 for m in metrics if m.fill_rate >= 95)
            report.failed_executions = report.total_executions - report.successful_executions
            
            # Calculate success rate
            if report.total_executions > 0:
                report.success_rate = (report.successful_executions / report.total_executions) * 100
            
            # Quality distribution
            report.excellent_executions = sum(1 for m in metrics 
                                            if m.quality_level == ExecutionQualityLevel.EXCELLENT)
            report.good_executions = sum(1 for m in metrics 
                                       if m.quality_level == ExecutionQualityLevel.GOOD)
            report.average_executions = sum(1 for m in metrics 
                                          if m.quality_level == ExecutionQualityLevel.AVERAGE)
            report.poor_executions = sum(1 for m in metrics 
                                       if m.quality_level == ExecutionQualityLevel.POOR)
            report.very_poor_executions = sum(1 for m in metrics 
                                            if m.quality_level == ExecutionQualityLevel.VERY_POOR)
            
            # Calculate quality distribution percentages
            total_quality_executions = (report.excellent_executions + report.good_executions + 
                                      report.average_executions + report.poor_executions + 
                                      report.very_poor_executions)
            
            if total_quality_executions > 0:
                report.excellent_pct = (report.excellent_executions / total_quality_executions) * 100
                report.good_pct = (report.good_executions / total_quality_executions) * 100
                report.average_pct = (report.average_executions / total_quality_executions) * 100
                report.poor_pct = (report.poor_executions / total_quality_executions) * 100
                report.very_poor_pct = (report.very_poor_executions / total_quality_executions) * 100
            
            # Average metrics
            if metrics:
                report.avg_fill_rate = np.mean([m.fill_rate for m in metrics])
                report.avg_implementation_shortfall = np.mean([abs(m.implementation_shortfall) for m in metrics])
                report.avg_market_impact = np.mean([abs(m.market_impact_cost) for m in metrics])
                report.avg_timing_cost = np.mean([abs(m.timing_cost) for m in metrics])
                report.avg_execution_time = np.mean([m.execution_time for m in metrics])
                report.avg_quality_score = np.mean([m.overall_quality_score for m in metrics])
                
                # Cost analysis
                report.total_execution_cost = sum(m.total_cost for m in metrics)
                report.avg_execution_cost = report.total_execution_cost / len(metrics)
                
                # Cost by type
                report.cost_by_type = {
                    ExecutionCostType.COMMISSION: np.mean([m.commission_cost for m in metrics]),
                    ExecutionCostType.SLIPPAGE: np.mean([m.slippage_cost for m in metrics]),
                    ExecutionCostType.MARKET_IMPACT: np.mean([m.market_impact_cost for m in metrics]),
                    ExecutionCostType.TIMING_COST: np.mean([m.timing_cost for m in metrics]),
                    ExecutionCostType.IMPLEMENTATION_SHORTFALL: np.mean([abs(m.implementation_shortfall) for m in metrics])
                }
            
        except Exception as e:
            logger.error(f"Error calculating report statistics: {e}")
            raise
    
    async def _generate_recommendations(self, report: ExecutionQualityReport,
                                      metrics: List[ExecutionQualityMetrics]):
        """
        Generate recommendations for improvement
        
        Args:
            report: Report to populate with recommendations
            metrics: List of quality metrics
        """
        try:
            recommendations = []
            opportunities = []
            
            # Analyze quality trends
            if len(metrics) >= 10:
                recent_metrics = metrics[-10:]
                older_metrics = metrics[-20:-10]
                
                recent_avg = np.mean([m.overall_quality_score for m in recent_metrics])
                older_avg = np.mean([m.overall_quality_score for m in older_metrics])
                
                if recent_avg > older_avg + 0.1:
                    report.quality_trend = "improving"
                elif recent_avg < older_avg - 0.1:
                    report.quality_trend = "declining"
                    recommendations.append("Execution quality is declining. Review recent changes to execution parameters.")
                else:
                    report.quality_trend = "stable"
            
            # Algorithm-specific recommendations
            algorithm_performance = {}
            for metric in metrics:
                algo = metric.algorithm
                if algo not in algorithm_performance:
                    algorithm_performance[algo] = []
                algorithm_performance[algo].append(metric.overall_quality_score)
            
            for algo, scores in algorithm_performance.items():
                avg_score = np.mean(scores)
                if avg_score < 0.6:
                    recommendations.append(f"Consider optimizing {algo.value} algorithm parameters")
                    opportunities.append(f"Improve {algo.value} algorithm performance")
            
            # Cost optimization opportunities
            avg_implementation_shortfall = np.mean([abs(m.implementation_shortfall) for m in metrics])
            if avg_implementation_shortfall > 0.003:  # 30 bps
                recommendations.append("High implementation shortfall detected. Consider adjusting urgency parameters.")
                opportunities.append("Reduce implementation shortfall through better timing")
            
            # Execution time optimization
            avg_execution_time = np.mean([m.execution_time for m in metrics])
            if avg_execution_time > 180:  # 3 minutes
                recommendations.append("Slow execution times detected. Consider using more aggressive algorithms.")
                opportunities.append("Reduce execution time through algorithm optimization")
            
            report.recommendations = recommendations
            report.improvement_opportunities = opportunities
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get current performance summary
        
        Returns:
            Performance summary dictionary
        """
        return {
            'total_executions': self.performance_metrics['total_executions'],
            'successful_executions': self.performance_metrics['successful_executions'],
            'success_rate': (self.performance_metrics['successful_executions'] / 
                           max(1, self.performance_metrics['total_executions'])) * 100,
            'avg_quality_score': self.performance_metrics['avg_quality_score'],
            'avg_fill_rate': self.performance_metrics['avg_fill_rate'],
            'avg_implementation_shortfall': self.performance_metrics['avg_implementation_shortfall'],
            'total_execution_cost': self.performance_metrics['total_execution_cost'],
            'recent_alerts': len([a for a in self.real_time_alerts 
                                if a['timestamp'] > datetime.now() - timedelta(hours=1)])
        }
    
    def get_quality_history(self, 
                          symbol: Optional[str] = None,
                          days: int = 30) -> List[ExecutionQualityMetrics]:
        """
        Get quality metrics history
        
        Args:
            symbol: Filter by symbol
            days: Number of days to look back
            
        Returns:
            List of quality metrics
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        filtered_metrics = [
            m for m in self.quality_metrics
            if m.timestamp >= cutoff_time
            and (symbol is None or m.symbol == symbol)
        ]
        
        return filtered_metrics
    
    def clear_old_data(self, retention_days: Optional[int] = None):
        """
        Clear old data based on retention policy
        
        Args:
            retention_days: Override retention days from config
        """
        try:
            retention_days = retention_days or self.config.retention_days
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            # Clear old quality metrics
            self.quality_metrics = [
                m for m in self.quality_metrics
                if m.timestamp >= cutoff_time
            ]
            
            # Clear old execution history
            # Note: ExecutionResult objects don't have timestamps, so we keep them all
            # The filtering is done on quality_metrics which have timestamps
            pass
            
            # Clear old reports
            self.quality_reports = [
                r for r in self.quality_reports
                if r.generated_at >= cutoff_time
            ]
            
            # Clear old alerts
            self.real_time_alerts = [
                a for a in self.real_time_alerts
                if a['timestamp'] >= cutoff_time
            ]
            
            logger.info(f"Cleared data older than {retention_days} days")
            
        except Exception as e:
            logger.error(f"Error clearing old data: {e}") 