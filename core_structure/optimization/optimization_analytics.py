"""
Optimization Analytics Module

Provides comprehensive analytics for optimization processes including:
- Optimization performance tracking
- Algorithm efficiency analysis
- Convergence monitoring
- Resource utilization tracking
- Optimization quality assessment

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class OptimizationStatus(Enum):
    """Optimization status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    CONVERGED = "converged"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class OptimizationType(Enum):
    """Optimization type enumeration"""
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    PARAMETER_OPTIMIZATION = "parameter_optimization"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    RISK_OPTIMIZATION = "risk_optimization"
    COST_OPTIMIZATION = "cost_optimization"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"


class ConvergenceType(Enum):
    """Convergence type enumeration"""
    GRADIENT_BASED = "gradient_based"
    POPULATION_BASED = "population_based"
    BAYESIAN = "bayesian"
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    HYBRID = "hybrid"


@dataclass
class OptimizationAnalyticsConfig:
    """Configuration for optimization analytics"""
    
    # Performance tracking settings
    track_iterations: bool = True
    track_objective_values: bool = True
    track_constraints: bool = True
    track_gradients: bool = False
    track_hessians: bool = False
    
    # Convergence settings
    convergence_tolerance: float = 1e-6
    max_iterations: int = 1000
    patience: int = 50  # Early stopping patience
    
    # Resource tracking
    track_memory_usage: bool = True
    track_cpu_usage: bool = True
    track_time: bool = True
    
    # Quality assessment
    quality_metrics: List[str] = field(default_factory=lambda: [
        "objective_improvement",
        "constraint_violation",
        "gradient_norm",
        "hessian_condition"
    ])
    
    # Retention settings
    retention_days: int = 30
    max_history_size: int = 10000
    
    # Alert settings
    alert_on_failure: bool = True
    alert_on_timeout: bool = True
    alert_on_poor_convergence: bool = True
    
    # Performance thresholds
    min_improvement_rate: float = 0.01
    max_constraint_violation: float = 1e-3
    max_gradient_norm: float = 1e-3


@dataclass
class OptimizationPerformance:
    """Optimization performance metrics"""
    
    # Basic information
    optimization_id: str
    optimization_type: OptimizationType
    algorithm_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: OptimizationStatus = OptimizationStatus.PENDING
    
    # Objective function metrics
    initial_objective: Optional[float] = None
    final_objective: Optional[float] = None
    best_objective: Optional[float] = None
    objective_history: List[float] = field(default_factory=list)
    
    # Iteration metrics
    total_iterations: int = 0
    successful_iterations: int = 0
    failed_iterations: int = 0
    
    # Convergence metrics
    convergence_type: Optional[ConvergenceType] = None
    convergence_rate: Optional[float] = None
    convergence_iterations: Optional[int] = None
    is_converged: bool = False
    
    # Constraint metrics
    constraint_violations: List[float] = field(default_factory=list)
    max_constraint_violation: Optional[float] = None
    final_constraint_violation: Optional[float] = None
    
    # Gradient metrics
    gradient_norms: List[float] = field(default_factory=list)
    final_gradient_norm: Optional[float] = None
    
    # Resource metrics
    memory_usage_mb: List[float] = field(default_factory=list)
    cpu_usage_percent: List[float] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    
    # Quality metrics
    optimization_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    quality_score: Optional[float] = None
    
    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # Metadata
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationReport:
    """Optimization analytics report"""
    
    # Report metadata
    report_id: str
    generation_time: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    # Summary statistics
    total_optimizations: int = 0
    successful_optimizations: int = 0
    failed_optimizations: int = 0
    success_rate: float = 0.0
    
    # Performance statistics
    avg_execution_time: float = 0.0
    avg_iterations: float = 0.0
    avg_convergence_rate: float = 0.0
    avg_optimization_score: float = 0.0
    
    # Quality distribution
    excellent_optimizations: int = 0
    good_optimizations: int = 0
    average_optimizations: int = 0
    poor_optimizations: int = 0
    very_poor_optimizations: int = 0
    
    # Type distribution
    optimization_type_distribution: Dict[str, int] = field(default_factory=dict)
    algorithm_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Performance trends
    performance_trends: Dict[str, List[float]] = field(default_factory=dict)


class OptimizationAnalytics:
    """
    Optimization Analytics System
    
    Provides comprehensive analytics for optimization processes including:
    - Performance tracking and monitoring
    - Convergence analysis
    - Resource utilization tracking
    - Quality assessment and scoring
    - Historical analysis and reporting
    """
    
    def __init__(self, config: Optional[OptimizationAnalyticsConfig] = None):
        """
        Initialize optimization analytics
        
        Args:
            config: Configuration for optimization analytics
        """
        self.config = config or OptimizationAnalyticsConfig()
        self.optimization_history: List[OptimizationPerformance] = []
        self.active_optimizations: Dict[str, OptimizationPerformance] = {}
        self.performance_metrics: Dict[str, Any] = {
            'total_optimizations': 0,
            'successful_optimizations': 0,
            'failed_optimizations': 0,
            'avg_execution_time': 0.0,
            'avg_optimization_score': 0.0
        }
        self.alerts: List[Dict[str, Any]] = []
        
        logger.info("OptimizationAnalytics initialized with config: %s", self.config)
    
    async def track_optimization(self, optimization_data: Dict[str, Any]) -> str:
        """
        Track an optimization process
        
        Args:
            optimization_data: Dictionary containing optimization data
            
        Returns:
            Optimization ID
        """
        try:
            # Extract basic information
            optimization_id = optimization_data.get('optimization_id', f"opt_{len(self.optimization_history)}")
            optimization_type = OptimizationType(optimization_data.get('optimization_type', 'parameter_optimization'))
            algorithm_name = optimization_data.get('algorithm_name', 'unknown')
            
            # Create optimization performance object
            performance = OptimizationPerformance(
                optimization_id=optimization_id,
                optimization_type=optimization_type,
                algorithm_name=algorithm_name,
                start_time=datetime.now(),
                parameters=optimization_data.get('parameters', {}),
                metadata=optimization_data.get('metadata', {})
            )
            
            # Track initial objective if available
            if 'initial_objective' in optimization_data:
                performance.initial_objective = optimization_data['initial_objective']
                performance.objective_history.append(performance.initial_objective)
            
            # Store in active optimizations
            self.active_optimizations[optimization_id] = performance
            
            # Update performance metrics
            self.performance_metrics['total_optimizations'] += 1
            
            logger.info("Started tracking optimization: %s", optimization_id)
            return optimization_id
            
        except Exception as e:
            logger.error("Error tracking optimization: %s", e)
            raise
    
    async def update_optimization(self, optimization_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an active optimization with new data
        
        Args:
            optimization_id: ID of the optimization to update
            update_data: Dictionary containing update data
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if optimization_id not in self.active_optimizations:
                logger.warning("Optimization %s not found in active optimizations", optimization_id)
                return False
            
            performance = self.active_optimizations[optimization_id]
            
            # Update iteration count
            if 'iteration' in update_data:
                performance.total_iterations = update_data['iteration']
            
            # Update objective value
            if 'objective_value' in update_data:
                performance.objective_history.append(update_data['objective_value'])
                performance.final_objective = update_data['objective_value']
                
                # Update best objective
                if (performance.best_objective is None or 
                    update_data['objective_value'] < performance.best_objective):
                    performance.best_objective = update_data['objective_value']
            
            # Update constraint violations
            if 'constraint_violation' in update_data:
                performance.constraint_violations.append(update_data['constraint_violation'])
                performance.final_constraint_violation = update_data['constraint_violation']
                
                if (performance.max_constraint_violation is None or 
                    update_data['constraint_violation'] > performance.max_constraint_violation):
                    performance.max_constraint_violation = update_data['constraint_violation']
            
            # Update gradient norm
            if 'gradient_norm' in update_data:
                performance.gradient_norms.append(update_data['gradient_norm'])
                performance.final_gradient_norm = update_data['gradient_norm']
            
            # Update resource usage
            if 'memory_usage_mb' in update_data:
                performance.memory_usage_mb.append(update_data['memory_usage_mb'])
            
            if 'cpu_usage_percent' in update_data:
                performance.cpu_usage_percent.append(update_data['cpu_usage_percent'])
            
            # Update status
            if 'status' in update_data:
                performance.status = OptimizationStatus(update_data['status'])
            
            # Check for completion
            if performance.status in [OptimizationStatus.CONVERGED, OptimizationStatus.FAILED, 
                                    OptimizationStatus.TIMEOUT, OptimizationStatus.CANCELLED]:
                await self._finalize_optimization(optimization_id)
            
            return True
            
        except Exception as e:
            logger.error("Error updating optimization %s: %s", optimization_id, e)
            return False
    
    async def _finalize_optimization(self, optimization_id: str):
        """
        Finalize an optimization and move to history
        
        Args:
            optimization_id: ID of the optimization to finalize
        """
        try:
            performance = self.active_optimizations[optimization_id]
            performance.end_time = datetime.now()
            
            # Calculate execution time
            if performance.start_time and performance.end_time:
                performance.execution_time_seconds = (
                    performance.end_time - performance.start_time
                ).total_seconds()
            
            # Calculate optimization scores
            await self._calculate_optimization_score(performance)
            
            # Move to history
            self.optimization_history.append(performance)
            del self.active_optimizations[optimization_id]
            
            # Update performance metrics
            if performance.status == OptimizationStatus.CONVERGED:
                self.performance_metrics['successful_optimizations'] += 1
            else:
                self.performance_metrics['failed_optimizations'] += 1
            
            # Update averages
            total_completed = self.performance_metrics['successful_optimizations'] + self.performance_metrics['failed_optimizations']
            if total_completed > 0:
                # Update execution time average
                current_avg = self.performance_metrics['avg_execution_time']
                new_time = performance.execution_time_seconds or 0.0
                self.performance_metrics['avg_execution_time'] = (
                    (current_avg * (total_completed - 1) + new_time) / total_completed
                )
                
                # Update optimization score average
                if performance.optimization_score is not None:
                    current_avg_score = self.performance_metrics['avg_optimization_score']
                    self.performance_metrics['avg_optimization_score'] = (
                        (current_avg_score * (total_completed - 1) + performance.optimization_score) / total_completed
                    )
            
            logger.info("Finalized optimization %s with status: %s", optimization_id, performance.status.value)
            
        except Exception as e:
            logger.error("Error finalizing optimization %s: %s", optimization_id, e)
    
    async def _calculate_optimization_score(self, performance: OptimizationPerformance):
        """
        Calculate optimization quality scores
        
        Args:
            performance: Optimization performance object to score
        """
        try:
            # Calculate optimization score based on objective improvement
            if (performance.initial_objective is not None and 
                performance.final_objective is not None):
                
                improvement = (performance.initial_objective - performance.final_objective) / abs(performance.initial_objective)
                performance.optimization_score = max(0.0, min(1.0, improvement))
            
            # Calculate efficiency score based on iterations and time
            if performance.total_iterations > 0 and performance.execution_time_seconds:
                # Normalize by expected iterations and time
                iteration_efficiency = min(1.0, self.config.max_iterations / performance.total_iterations)
                time_efficiency = min(1.0, 60.0 / performance.execution_time_seconds)  # Assume 60s is good
                performance.efficiency_score = (iteration_efficiency + time_efficiency) / 2
            
            # Calculate overall quality score
            scores = []
            if performance.optimization_score is not None:
                scores.append(performance.optimization_score)
            if performance.efficiency_score is not None:
                scores.append(performance.efficiency_score)
            
            if scores:
                performance.quality_score = np.mean(scores)
            
            # Check convergence
            if (performance.final_gradient_norm is not None and 
                performance.final_gradient_norm < self.config.max_gradient_norm):
                performance.is_converged = True
            
        except Exception as e:
            logger.error("Error calculating optimization score: %s", e)
    
    async def generate_optimization_report(self, 
                                         start_time: Optional[datetime] = None,
                                         end_time: Optional[datetime] = None) -> OptimizationReport:
        """
        Generate optimization analytics report
        
        Args:
            start_time: Start time for report period
            end_time: End time for report period
            
        Returns:
            Optimization analytics report
        """
        try:
            # Filter optimizations by time period
            if start_time is None:
                start_time = datetime.now() - timedelta(days=7)
            if end_time is None:
                end_time = datetime.now()
            
            filtered_optimizations = [
                opt for opt in self.optimization_history
                if start_time <= opt.start_time <= end_time
            ]
            
            # Create report
            report = OptimizationReport(
                report_id=f"opt_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                generation_time=datetime.now(),
                period_start=start_time,
                period_end=end_time,
                total_optimizations=len(filtered_optimizations)
            )
            
            if filtered_optimizations:
                # Calculate success rate
                successful = sum(1 for opt in filtered_optimizations 
                               if opt.status == OptimizationStatus.CONVERGED)
                report.successful_optimizations = successful
                report.failed_optimizations = len(filtered_optimizations) - successful
                report.success_rate = (successful / len(filtered_optimizations)) * 100
                
                # Calculate averages
                execution_times = [opt.execution_time_seconds for opt in filtered_optimizations 
                                 if opt.execution_time_seconds is not None]
                if execution_times:
                    report.avg_execution_time = np.mean(execution_times)
                
                iterations = [opt.total_iterations for opt in filtered_optimizations]
                if iterations:
                    report.avg_iterations = np.mean(iterations)
                
                convergence_rates = [opt.convergence_rate for opt in filtered_optimizations 
                                   if opt.convergence_rate is not None]
                if convergence_rates:
                    report.avg_convergence_rate = np.mean(convergence_rates)
                
                optimization_scores = [opt.optimization_score for opt in filtered_optimizations 
                                     if opt.optimization_score is not None]
                if optimization_scores:
                    report.avg_optimization_score = np.mean(optimization_scores)
                
                # Calculate quality distribution
                for opt in filtered_optimizations:
                    if opt.quality_score is not None:
                        if opt.quality_score >= 0.8:
                            report.excellent_optimizations += 1
                        elif opt.quality_score >= 0.6:
                            report.good_optimizations += 1
                        elif opt.quality_score >= 0.4:
                            report.average_optimizations += 1
                        elif opt.quality_score >= 0.2:
                            report.poor_optimizations += 1
                        else:
                            report.very_poor_optimizations += 1
                
                # Calculate type distribution
                for opt in filtered_optimizations:
                    opt_type = opt.optimization_type.value
                    report.optimization_type_distribution[opt_type] = (
                        report.optimization_type_distribution.get(opt_type, 0) + 1
                    )
                    
                    algorithm = opt.algorithm_name
                    report.algorithm_distribution[algorithm] = (
                        report.algorithm_distribution.get(algorithm, 0) + 1
                    )
                
                # Generate recommendations
                if report.success_rate < 80:
                    report.recommendations.append("Consider adjusting optimization parameters to improve success rate")
                
                if report.avg_execution_time > 300:  # 5 minutes
                    report.recommendations.append("Optimization execution time is high, consider algorithm tuning")
                
                if report.avg_optimization_score < 0.5:
                    report.recommendations.append("Optimization quality is low, review objective function and constraints")
            
            logger.info("Generated optimization report with %d optimizations", len(filtered_optimizations))
            return report
            
        except Exception as e:
            logger.error("Error generating optimization report: %s", e)
            raise
    
    def get_optimization_status(self, optimization_id: str) -> Optional[OptimizationPerformance]:
        """
        Get status of an optimization
        
        Args:
            optimization_id: ID of the optimization
            
        Returns:
            Optimization performance object or None if not found
        """
        # Check active optimizations first
        if optimization_id in self.active_optimizations:
            return self.active_optimizations[optimization_id]
        
        # Check history
        for opt in self.optimization_history:
            if opt.optimization_id == optimization_id:
                return opt
        
        return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary
        
        Returns:
            Dictionary containing performance summary
        """
        return self.performance_metrics.copy()
    
    def clear_old_data(self, retention_days: Optional[int] = None):
        """
        Clear old optimization data
        
        Args:
            retention_days: Number of days to retain data
        """
        try:
            retention_days = retention_days or self.config.retention_days
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            # Clear old history
            original_count = len(self.optimization_history)
            self.optimization_history = [
                opt for opt in self.optimization_history
                if opt.start_time >= cutoff_time
            ]
            
            removed_count = original_count - len(self.optimization_history)
            logger.info("Cleared %d old optimization records", removed_count)
            
        except Exception as e:
            logger.error("Error clearing old data: %s", e) 