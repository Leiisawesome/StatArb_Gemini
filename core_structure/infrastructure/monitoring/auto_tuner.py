"""
Auto-Tuner
==========

Automated performance tuning system that combines real-time monitoring
with continuous optimization for autonomous performance management.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum

from .real_time_monitor import RealTimeMonitor, MonitorConfig, MetricType, PerformanceAlert
from .continuous_optimizer import ContinuousOptimizer, OptimizerConfig, Parameter, ParameterType

logger = logging.getLogger(__name__)

class TuningMode(Enum):
    """Auto-tuning modes"""
    CONSERVATIVE = "conservative"  # Small, safe changes
    AGGRESSIVE = "aggressive"     # Larger optimization steps
    EXPLORATORY = "exploratory"   # Wide parameter exploration
    RECOVERY = "recovery"         # Focus on stability recovery

class TuningPhase(Enum):
    """Auto-tuning phases"""
    BASELINE = "baseline"         # Establishing baseline performance
    OPTIMIZATION = "optimization" # Active optimization
    VALIDATION = "validation"     # Validating improvements
    MAINTENANCE = "maintenance"   # Maintaining optimal performance

@dataclass
class AutoTunerConfig:
    """Configuration for auto-tuner"""
    # Tuning behavior
    tuning_mode: TuningMode = TuningMode.CONSERVATIVE
    enable_automatic_tuning: bool = True
    enable_rollback_protection: bool = True
    
    # Performance targets
    target_latency_ms: float = 1.0
    target_throughput_improvement: float = 0.2  # 20% improvement
    target_error_rate: float = 0.01  # 1%
    
    # Timing settings
    baseline_duration_seconds: int = 300  # 5 minutes
    optimization_cycle_seconds: int = 60  # 1 minute
    validation_duration_seconds: int = 180  # 3 minutes
    
    # Safety settings
    max_degradation_tolerance: float = 0.05  # 5% degradation before rollback
    rollback_sensitivity: float = 3  # Number of alerts before rollback
    recovery_timeout_seconds: int = 300  # 5 minutes

@dataclass
class TuningSession:
    """Auto-tuning session tracking"""
    session_id: str
    start_time: datetime
    phase: TuningPhase
    mode: TuningMode
    baseline_performance: Dict[str, float]
    current_performance: Dict[str, float]
    optimizations_applied: List[Dict[str, Any]]
    alerts_received: List[PerformanceAlert]
    improvements_achieved: Dict[str, float]

class PerformanceBaseline:
    """Manages performance baselines for auto-tuning"""
    
    def __init__(self):
        self.baselines: Dict[str, Dict[str, float]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def establish_baseline(self, component_name: str, metrics: Dict[str, float]):
        """Establish performance baseline for component"""
        self.baselines[component_name] = metrics.copy()
        self.logger.info(f"Established baseline for {component_name}: {metrics}")
    
    def get_baseline(self, component_name: str) -> Dict[str, float]:
        """Get baseline performance for component"""
        return self.baselines.get(component_name, {})
    
    def calculate_improvement(self, component_name: str, current_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate performance improvement vs baseline"""
        baseline = self.get_baseline(component_name)
        if not baseline:
            return {}
        
        improvements = {}
        for metric_name, current_value in current_metrics.items():
            if metric_name in baseline:
                baseline_value = baseline[metric_name]
                
                # For latency metrics, lower is better
                if 'latency' in metric_name.lower() or 'time' in metric_name.lower():
                    improvement = (baseline_value - current_value) / baseline_value if baseline_value > 0 else 0
                else:
                    # For throughput metrics, higher is better
                    improvement = (current_value - baseline_value) / baseline_value if baseline_value > 0 else 0
                
                improvements[metric_name] = improvement
        
        return improvements

class RollbackManager:
    """Manages rollback of optimization changes"""
    
    def __init__(self):
        self.rollback_points: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_rollback_point(self, component_name: str, component: Any, parameters: Dict[str, Parameter]):
        """Create rollback point before optimization"""
        rollback_data = {}
        
        for param_name, parameter in parameters.items():
            rollback_data[param_name] = parameter.current_value
        
        self.rollback_points[component_name] = rollback_data
        self.logger.info(f"Created rollback point for {component_name}")
    
    def rollback_component(self, component_name: str, component: Any, parameters: Dict[str, Parameter]) -> bool:
        """Rollback component to previous configuration"""
        if component_name not in self.rollback_points:
            self.logger.warning(f"No rollback point available for {component_name}")
            return False
        
        rollback_data = self.rollback_points[component_name]
        success_count = 0
        
        for param_name, rollback_value in rollback_data.items():
            if param_name in parameters:
                try:
                    # Apply rollback value
                    if hasattr(component, param_name):
                        setattr(component, param_name, rollback_value)
                        success_count += 1
                    elif hasattr(component, 'config') and hasattr(component.config, param_name):
                        setattr(component.config, param_name, rollback_value)
                        success_count += 1
                    
                    # Update parameter tracking
                    parameters[param_name].current_value = rollback_value
                    
                except Exception as e:
                    self.logger.error(f"Failed to rollback parameter {param_name}: {e}")
        
        if success_count > 0:
            self.logger.info(f"Rolled back {success_count} parameters for {component_name}")
            return True
        else:
            self.logger.error(f"Failed to rollback any parameters for {component_name}")
            return False

class AutoTuner:
    """
    Automated performance tuner that combines real-time monitoring
    with continuous optimization for autonomous performance management.
    """
    
    def __init__(self, config: Optional[AutoTunerConfig] = None):
        self.config = config or AutoTunerConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize monitoring and optimization
        monitor_config = MonitorConfig(
            monitoring_interval_ms=100,
            max_latency_ms=self.config.target_latency_ms * 2,
            max_error_rate=self.config.target_error_rate * 2
        )
        
        optimizer_config = OptimizerConfig(
            optimization_interval_seconds=self.config.optimization_cycle_seconds,
            degradation_threshold=self.config.max_degradation_tolerance
        )
        
        self.monitor = RealTimeMonitor(monitor_config)
        self.optimizer = ContinuousOptimizer(optimizer_config)
        
        # Auto-tuning components
        self.baseline_manager = PerformanceBaseline()
        self.rollback_manager = RollbackManager()
        
        # Tuning state
        self.is_tuning = False
        self.current_session: Optional[TuningSession] = None
        self.tuning_thread: Optional[threading.Thread] = None
        self.registered_components: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.alert_count_per_component: Dict[str, int] = {}
        self.total_tuning_sessions = 0
        self.successful_tuning_sessions = 0
        
        # Register alert callback
        self.monitor.register_alert_callback(self._handle_performance_alert)
        
        self.logger.info(f"AutoTuner initialized - Mode: {self.config.tuning_mode.value}")
    
    def register_component(self, component_name: str, component: Any, 
                          parameters: Dict[str, Parameter]):
        """Register component for auto-tuning"""
        self.registered_components[component_name] = {
            'component': component,
            'parameters': parameters,
            'baseline_established': False,
            'optimization_enabled': True
        }
        
        # Register with monitor and optimizer
        self.monitor.register_component(component_name, component)
        self.optimizer.register_component(component_name, component, parameters)
        
        self.alert_count_per_component[component_name] = 0
        
        self.logger.info(f"Registered component for auto-tuning: {component_name}")
    
    def start_auto_tuning(self):
        """Start automated performance tuning"""
        if self.is_tuning:
            self.logger.warning("Auto-tuning is already running")
            return
        
        self.is_tuning = True
        
        # Start monitoring and optimization
        self.monitor.start_monitoring()
        self.optimizer.start_optimization()
        
        # Start tuning coordination thread
        self.tuning_thread = threading.Thread(target=self._tuning_coordination_loop, daemon=True)
        self.tuning_thread.start()
        
        self.logger.info("Auto-tuning started")
    
    def stop_auto_tuning(self):
        """Stop automated performance tuning"""
        self.is_tuning = False
        
        # Stop monitoring and optimization
        self.monitor.stop_monitoring()
        self.optimizer.stop_optimization()
        
        # Stop tuning thread
        if self.tuning_thread:
            self.tuning_thread.join(timeout=2.0)
        
        self.logger.info("Auto-tuning stopped")
    
    def get_tuning_status(self) -> Dict[str, Any]:
        """Get current auto-tuning status"""
        monitor_status = self.monitor.get_overall_status()
        optimizer_status = self.optimizer.get_optimization_status()
        
        return {
            'auto_tuning_active': self.is_tuning,
            'tuning_mode': self.config.tuning_mode.value,
            'current_phase': self.current_session.phase.value if self.current_session else None,
            'total_sessions': self.total_tuning_sessions,
            'successful_sessions': self.successful_tuning_sessions,
            'session_success_rate': (self.successful_tuning_sessions / max(1, self.total_tuning_sessions)) * 100,
            'monitoring_status': monitor_status,
            'optimization_status': optimizer_status,
            'component_baselines': dict(self.baseline_manager.baselines),
            'alert_counts': dict(self.alert_count_per_component)
        }
    
    def _tuning_coordination_loop(self):
        """Main auto-tuning coordination loop"""
        self.logger.info("Starting auto-tuning coordination loop")
        
        while self.is_tuning:
            try:
                if not self.current_session:
                    self._start_new_tuning_session()
                
                if self.current_session:
                    self._process_tuning_session()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Auto-tuning coordination error: {e}")
                time.sleep(30)  # Error recovery delay
    
    def _start_new_tuning_session(self):
        """Start a new auto-tuning session"""
        session_id = f"tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = TuningSession(
            session_id=session_id,
            start_time=datetime.now(),
            phase=TuningPhase.BASELINE,
            mode=self.config.tuning_mode,
            baseline_performance={},
            current_performance={},
            optimizations_applied=[],
            alerts_received=[],
            improvements_achieved={}
        )
        
        self.total_tuning_sessions += 1
        
        self.logger.info(f"Started new tuning session: {session_id}")
    
    def _process_tuning_session(self):
        """Process current tuning session based on phase"""
        if not self.current_session:
            return
        
        session_age = (datetime.now() - self.current_session.start_time).total_seconds()
        
        if self.current_session.phase == TuningPhase.BASELINE:
            self._process_baseline_phase(session_age)
        elif self.current_session.phase == TuningPhase.OPTIMIZATION:
            self._process_optimization_phase(session_age)
        elif self.current_session.phase == TuningPhase.VALIDATION:
            self._process_validation_phase(session_age)
        elif self.current_session.phase == TuningPhase.MAINTENANCE:
            self._process_maintenance_phase(session_age)
    
    def _process_baseline_phase(self, session_age: float):
        """Process baseline establishment phase"""
        if session_age < self.config.baseline_duration_seconds:
            return  # Still collecting baseline data
        
        # Establish baselines for all components
        for component_name in self.registered_components.keys():
            component_status = self.monitor.get_component_status(component_name)
            
            if component_status.get('metrics'):
                baseline_metrics = {}
                for metric_type, stats in component_status['metrics'].items():
                    if isinstance(stats, dict) and 'mean' in stats:
                        baseline_metrics[metric_type] = stats['mean']
                
                if baseline_metrics:
                    self.baseline_manager.establish_baseline(component_name, baseline_metrics)
                    self.current_session.baseline_performance[component_name] = baseline_metrics
                    self.registered_components[component_name]['baseline_established'] = True
        
        # Move to optimization phase
        self.current_session.phase = TuningPhase.OPTIMIZATION
        self.logger.info(f"Session {self.current_session.session_id}: Moving to optimization phase")
    
    def _process_optimization_phase(self, session_age: float):
        """Process active optimization phase"""
        # Check for excessive alerts (indicating instability)
        total_alerts = sum(self.alert_count_per_component.values())
        
        if total_alerts > self.config.rollback_sensitivity:
            self.logger.warning(f"Excessive alerts detected ({total_alerts}), triggering rollback")
            self._trigger_rollback()
            return
        
        # Monitor performance improvements
        improvements_detected = False
        
        for component_name, component_info in self.registered_components.items():
            if not component_info['baseline_established']:
                continue
            
            component_status = self.monitor.get_component_status(component_name)
            
            if component_status.get('metrics'):
                current_metrics = {}
                for metric_type, stats in component_status['metrics'].items():
                    if isinstance(stats, dict) and 'mean' in stats:
                        current_metrics[metric_type] = stats['mean']
                
                if current_metrics:
                    improvements = self.baseline_manager.calculate_improvement(component_name, current_metrics)
                    
                    if improvements:
                        self.current_session.improvements_achieved[component_name] = improvements
                        
                        # Check if we've achieved target improvements
                        for metric_name, improvement in improvements.items():
                            if improvement > self.config.target_throughput_improvement:
                                improvements_detected = True
        
        # Move to validation if significant improvements detected
        if improvements_detected and session_age > 300:  # At least 5 minutes of optimization
            self.current_session.phase = TuningPhase.VALIDATION
            self.logger.info(f"Session {self.current_session.session_id}: Moving to validation phase")
    
    def _process_validation_phase(self, session_age: float):
        """Process validation phase"""
        # Monitor stability during validation
        validation_start = self.current_session.start_time + timedelta(seconds=self.config.baseline_duration_seconds + 300)
        validation_age = (datetime.now() - validation_start).total_seconds()
        
        if validation_age < self.config.validation_duration_seconds:
            return  # Still validating
        
        # Validate improvements are sustained
        sustained_improvements = True
        
        for component_name, component_info in self.registered_components.items():
            if not component_info['baseline_established']:
                continue
            
            component_status = self.monitor.get_component_status(component_name)
            
            if component_status.get('metrics'):
                current_metrics = {}
                for metric_type, stats in component_status['metrics'].items():
                    if isinstance(stats, dict) and 'mean' in stats:
                        current_metrics[metric_type] = stats['mean']
                
                if current_metrics:
                    improvements = self.baseline_manager.calculate_improvement(component_name, current_metrics)
                    
                    # Check if improvements are sustained
                    for metric_name, improvement in improvements.items():
                        if improvement < self.config.target_throughput_improvement * 0.8:  # 80% of target
                            sustained_improvements = False
                            break
        
        if sustained_improvements:
            self.current_session.phase = TuningPhase.MAINTENANCE
            self.successful_tuning_sessions += 1
            self.logger.info(f"Session {self.current_session.session_id}: Validation successful, moving to maintenance")
        else:
            self.logger.warning(f"Session {self.current_session.session_id}: Validation failed, triggering rollback")
            self._trigger_rollback()
    
    def _process_maintenance_phase(self, session_age: float):
        """Process maintenance phase"""
        # Monitor for performance degradation
        degradation_detected = False
        
        for component_name, component_info in self.registered_components.items():
            if not component_info['baseline_established']:
                continue
            
            component_status = self.monitor.get_component_status(component_name)
            
            if component_status.get('metrics'):
                current_metrics = {}
                for metric_type, stats in component_status['metrics'].items():
                    if isinstance(stats, dict) and 'mean' in stats:
                        current_metrics[metric_type] = stats['mean']
                
                if current_metrics:
                    improvements = self.baseline_manager.calculate_improvement(component_name, current_metrics)
                    
                    # Check for significant degradation
                    for metric_name, improvement in improvements.items():
                        if improvement < -self.config.max_degradation_tolerance:
                            degradation_detected = True
                            break
        
        if degradation_detected:
            self.logger.warning(f"Session {self.current_session.session_id}: Degradation detected in maintenance")
            self._trigger_rollback()
        elif session_age > 3600:  # 1 hour sessions
            # Start new session
            self._complete_current_session()
    
    def _trigger_rollback(self):
        """Trigger rollback of optimizations"""
        self.logger.info(f"Triggering rollback for session {self.current_session.session_id}")
        
        # Rollback all components
        for component_name, component_info in self.registered_components.items():
            component = component_info['component']
            parameters = component_info['parameters']
            
            # Create rollback point if not exists
            if component_name not in self.rollback_manager.rollback_points:
                self.rollback_manager.create_rollback_point(component_name, component, parameters)
            
            # Perform rollback
            self.rollback_manager.rollback_component(component_name, component, parameters)
        
        # Reset alert counts
        for component_name in self.alert_count_per_component:
            self.alert_count_per_component[component_name] = 0
        
        # Start new session
        self._complete_current_session()
    
    def _complete_current_session(self):
        """Complete current tuning session"""
        if self.current_session:
            session_duration = (datetime.now() - self.current_session.start_time).total_seconds()
            self.logger.info(f"Completed tuning session {self.current_session.session_id} "
                           f"after {session_duration:.0f} seconds")
            
            self.current_session = None
    
    def _handle_performance_alert(self, alert: PerformanceAlert):
        """Handle performance alert from monitor"""
        self.alert_count_per_component[alert.component] = self.alert_count_per_component.get(alert.component, 0) + 1
        
        if self.current_session:
            self.current_session.alerts_received.append(alert)
        
        self.logger.warning(f"Performance alert received: {alert.component} - {alert.message}")
