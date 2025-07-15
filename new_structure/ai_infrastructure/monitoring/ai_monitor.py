#!/usr/bin/env python3
"""
AI Infrastructure Monitoring System

Comprehensive monitoring and performance tracking for AI trading infrastructure:
- Agent performance monitoring and health checks
- LLM usage tracking and cost management
- System performance metrics and alerts
- Automated anomaly detection and alerting
- Dashboard integration and reporting

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class PerformanceMetrics:
    """Performance metrics structure"""
    response_time_ms: float = 0.0
    success_rate: float = 1.0
    error_rate: float = 0.0
    throughput_per_sec: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class Alert:
    """Alert structure"""
    alert_id: str
    severity: AlertSeverity
    component: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class AgentHealth:
    """Agent health information"""
    agent_id: str
    agent_type: str
    status: HealthStatus
    last_heartbeat: datetime
    response_time: float
    success_rate: float
    error_count: int
    performance_metrics: PerformanceMetrics


class AIMonitor:
    """
    Comprehensive AI infrastructure monitoring system
    
    Features:
    - Real-time agent performance tracking
    - LLM usage and cost monitoring
    - System health checks and alerting
    - Performance analytics and reporting
    - Automated anomaly detection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize AI monitoring system"""
        self.config = config or {}
        
        # Performance tracking
        self.agent_metrics = {}
        self.llm_metrics = {}
        self.system_metrics = {}
        
        # Health monitoring
        self.agent_health = {}
        self.system_health = HealthStatus.HEALTHY
        
        # Alert system
        self.active_alerts = []
        self.alert_history = deque(maxlen=10000)
        self.alert_callbacks = []
        
        # Performance history (keep last 1000 data points)
        self.performance_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Monitoring configuration
        self.monitoring_config = {
            'health_check_interval': 30,  # seconds
            'metrics_retention_hours': 24,
            'alert_thresholds': {
                'response_time_ms': 5000,
                'error_rate_threshold': 0.05,
                'memory_usage_mb': 1000,
                'cpu_usage_percent': 80
            },
            'anomaly_detection': {
                'enabled': True,
                'sensitivity': 0.8,
                'min_data_points': 10
            }
        }
        self.monitoring_config.update(config or {})
        
        # Background monitoring
        self._monitoring_active = False
        self._monitoring_task = None
        
        logger.info("AI Monitor initialized successfully")
    
    async def start_monitoring(self):
        """Start background monitoring tasks"""
        if self._monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("AI monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring tasks"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("AI monitoring stopped")
    
    def register_agent(self, agent_id: str, agent_type: str):
        """Register an agent for monitoring"""
        self.agent_metrics[agent_id] = PerformanceMetrics()
        self.agent_health[agent_id] = AgentHealth(
            agent_id=agent_id,
            agent_type=agent_type,
            status=HealthStatus.HEALTHY,
            last_heartbeat=datetime.now(),
            response_time=0.0,
            success_rate=1.0,
            error_count=0,
            performance_metrics=PerformanceMetrics()
        )
        logger.info(f"Agent {agent_id} registered for monitoring")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from monitoring"""
        self.agent_metrics.pop(agent_id, None)
        self.agent_health.pop(agent_id, None)
        logger.info(f"Agent {agent_id} unregistered from monitoring")
    
    async def record_agent_performance(self, agent_id: str, response_time: float, success: bool, memory_usage: float = 0.0):
        """Record agent performance metrics"""
        if agent_id not in self.agent_metrics:
            logger.warning(f"Agent {agent_id} not registered for monitoring")
            return
        
        metrics = self.agent_metrics[agent_id]
        
        # Update response time (exponential moving average)
        alpha = 0.3
        metrics.response_time_ms = alpha * response_time + (1 - alpha) * metrics.response_time_ms
        
        # Update success/error rates
        if success:
            metrics.success_rate = alpha * 1.0 + (1 - alpha) * metrics.success_rate
            metrics.error_rate = (1 - alpha) * metrics.error_rate
        else:
            metrics.success_rate = (1 - alpha) * metrics.success_rate
            metrics.error_rate = alpha * 1.0 + (1 - alpha) * metrics.error_rate
        
        # Update memory usage
        if memory_usage > 0:
            metrics.memory_usage_mb = memory_usage
        
        metrics.last_updated = datetime.now()
        
        # Update agent health
        if agent_id in self.agent_health:
            health = self.agent_health[agent_id]
            health.last_heartbeat = datetime.now()
            health.response_time = metrics.response_time_ms
            health.success_rate = metrics.success_rate
            
            if not success:
                health.error_count += 1
            
            # Update health status
            health.status = self._calculate_agent_health_status(metrics)
        
        # Store performance history
        self.performance_history[f"{agent_id}_response_time"].append((datetime.now(), response_time))
        self.performance_history[f"{agent_id}_success_rate"].append((datetime.now(), metrics.success_rate))
        
        # Check for alerts
        await self._check_agent_alerts(agent_id, metrics)
    
    async def record_llm_usage(self, model: str, tokens_used: int, cost: float, response_time: float, success: bool):
        """Record LLM usage metrics"""
        if model not in self.llm_metrics:
            self.llm_metrics[model] = {
                'total_tokens': 0,
                'total_cost': 0.0,
                'total_requests': 0,
                'successful_requests': 0,
                'avg_response_time': 0.0,
                'last_used': datetime.now()
            }
        
        metrics = self.llm_metrics[model]
        metrics['total_tokens'] += tokens_used
        metrics['total_cost'] += cost
        metrics['total_requests'] += 1
        
        if success:
            metrics['successful_requests'] += 1
        
        # Update average response time
        alpha = 0.3
        metrics['avg_response_time'] = alpha * response_time + (1 - alpha) * metrics['avg_response_time']
        metrics['last_used'] = datetime.now()
        
        # Store history
        self.performance_history[f"llm_{model}_tokens"].append((datetime.now(), tokens_used))
        self.performance_history[f"llm_{model}_cost"].append((datetime.now(), cost))
        
        # Check for cost alerts
        await self._check_llm_cost_alerts(model, metrics)
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            health_report = {
                'overall_status': self.system_health,
                'timestamp': datetime.now(),
                'agents': {},
                'llm_services': {},
                'system_metrics': {},
                'active_alerts': len(self.active_alerts),
                'performance_summary': {}
            }
            
            # Agent health summary
            for agent_id, health in self.agent_health.items():
                health_report['agents'][agent_id] = {
                    'status': health.status,
                    'last_heartbeat': health.last_heartbeat,
                    'response_time': health.response_time,
                    'success_rate': health.success_rate,
                    'error_count': health.error_count
                }
            
            # LLM service health
            for model, metrics in self.llm_metrics.items():
                success_rate = metrics['successful_requests'] / max(metrics['total_requests'], 1)
                health_report['llm_services'][model] = {
                    'status': 'healthy' if success_rate > 0.95 else 'warning' if success_rate > 0.8 else 'critical',
                    'success_rate': success_rate,
                    'avg_response_time': metrics['avg_response_time'],
                    'total_cost': metrics['total_cost'],
                    'last_used': metrics['last_used']
                }
            
            # System performance summary
            if self.agent_metrics:
                avg_response_time = np.mean([m.response_time_ms for m in self.agent_metrics.values()])
                avg_success_rate = np.mean([m.success_rate for m in self.agent_metrics.values()])
                total_memory = sum([m.memory_usage_mb for m in self.agent_metrics.values()])
                
                health_report['performance_summary'] = {
                    'avg_response_time_ms': avg_response_time,
                    'avg_success_rate': avg_success_rate,
                    'total_memory_usage_mb': total_memory,
                    'active_agents': len(self.agent_metrics)
                }
            
            return health_report
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e), 'timestamp': datetime.now()}
    
    async def get_performance_analytics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get performance analytics for specified time range"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            analytics = {
                'time_range': {'start': start_time, 'end': end_time},
                'agent_analytics': {},
                'llm_analytics': {},
                'system_trends': {},
                'anomalies_detected': []
            }
            
            # Agent performance analytics
            for agent_id in self.agent_metrics.keys():
                agent_analytics = await self._calculate_agent_analytics(agent_id, start_time, end_time)
                analytics['agent_analytics'][agent_id] = agent_analytics
            
            # LLM usage analytics
            for model in self.llm_metrics.keys():
                llm_analytics = await self._calculate_llm_analytics(model, start_time, end_time)
                analytics['llm_analytics'][model] = llm_analytics
            
            # System trend analysis
            analytics['system_trends'] = await self._calculate_system_trends(start_time, end_time)
            
            # Anomaly detection
            if self.monitoring_config['anomaly_detection']['enabled']:
                analytics['anomalies_detected'] = await self._detect_anomalies(start_time, end_time)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting performance analytics: {e}")
            return {'error': str(e)}
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add callback function for alert notifications"""
        self.alert_callbacks.append(callback)
        logger.info("Alert callback registered")
    
    def remove_alert_callback(self, callback: Callable[[Alert], None]):
        """Remove alert callback function"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            logger.info("Alert callback removed")
    
    async def resolve_alert(self, alert_id: str, resolution_notes: str = ""):
        """Resolve an active alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_time = datetime.now()
                alert.details['resolution_notes'] = resolution_notes
                
                # Move to history
                self.alert_history.append(alert)
                self.active_alerts.remove(alert)
                
                logger.info(f"Alert {alert_id} resolved: {resolution_notes}")
                return True
        
        logger.warning(f"Alert {alert_id} not found in active alerts")
        return False
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Update system health
                await self._update_system_health()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Sleep until next check
                await asyncio.sleep(self.monitoring_config['health_check_interval'])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _perform_health_checks(self):
        """Perform health checks on all monitored components"""
        current_time = datetime.now()
        
        # Check agent health
        for agent_id, health in self.agent_health.items():
            time_since_heartbeat = (current_time - health.last_heartbeat).total_seconds()
            
            if time_since_heartbeat > 300:  # 5 minutes
                health.status = HealthStatus.OFFLINE
                await self._create_alert(
                    AlertSeverity.HIGH,
                    f"agent_{agent_id}",
                    f"Agent {agent_id} appears offline - no heartbeat for {time_since_heartbeat:.0f}s",
                    {'agent_id': agent_id, 'last_heartbeat': health.last_heartbeat}
                )
            elif time_since_heartbeat > 120:  # 2 minutes
                health.status = HealthStatus.WARNING
                await self._create_alert(
                    AlertSeverity.MEDIUM,
                    f"agent_{agent_id}",
                    f"Agent {agent_id} heartbeat delayed - {time_since_heartbeat:.0f}s since last update",
                    {'agent_id': agent_id, 'last_heartbeat': health.last_heartbeat}
                )
    
    async def _update_system_health(self):
        """Update overall system health status"""
        if not self.agent_health:
            self.system_health = HealthStatus.WARNING
            return
        
        # Count health statuses
        status_counts = defaultdict(int)
        for health in self.agent_health.values():
            status_counts[health.status] += 1
        
        total_agents = len(self.agent_health)
        
        # Determine overall health
        if status_counts[HealthStatus.CRITICAL] > 0 or status_counts[HealthStatus.OFFLINE] > total_agents * 0.5:
            self.system_health = HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > total_agents * 0.3:
            self.system_health = HealthStatus.WARNING
        else:
            self.system_health = HealthStatus.HEALTHY
    
    async def _cleanup_old_data(self):
        """Clean up old performance data"""
        current_time = datetime.now()
        retention_hours = self.monitoring_config['metrics_retention_hours']
        cutoff_time = current_time - timedelta(hours=retention_hours)
        
        # Clean up performance history
        for key, history in self.performance_history.items():
            while history and history[0][0] < cutoff_time:
                history.popleft()
        
        # Clean up old alerts from history
        self.alert_history = deque([
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ], maxlen=10000)
    
    def _calculate_agent_health_status(self, metrics: PerformanceMetrics) -> HealthStatus:
        """Calculate agent health status based on metrics"""
        thresholds = self.monitoring_config['alert_thresholds']
        
        if (metrics.response_time_ms > thresholds['response_time_ms'] * 2 or
            metrics.error_rate > thresholds['error_rate_threshold'] * 3 or
            metrics.memory_usage_mb > thresholds['memory_usage_mb'] * 1.5):
            return HealthStatus.CRITICAL
        
        if (metrics.response_time_ms > thresholds['response_time_ms'] or
            metrics.error_rate > thresholds['error_rate_threshold'] or
            metrics.memory_usage_mb > thresholds['memory_usage_mb']):
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _check_agent_alerts(self, agent_id: str, metrics: PerformanceMetrics):
        """Check for agent performance alerts"""
        thresholds = self.monitoring_config['alert_thresholds']
        
        # Response time alert
        if metrics.response_time_ms > thresholds['response_time_ms']:
            severity = AlertSeverity.HIGH if metrics.response_time_ms > thresholds['response_time_ms'] * 2 else AlertSeverity.MEDIUM
            await self._create_alert(
                severity,
                f"agent_{agent_id}",
                f"High response time for agent {agent_id}: {metrics.response_time_ms:.1f}ms",
                {'agent_id': agent_id, 'response_time': metrics.response_time_ms, 'threshold': thresholds['response_time_ms']}
            )
        
        # Error rate alert
        if metrics.error_rate > thresholds['error_rate_threshold']:
            severity = AlertSeverity.HIGH if metrics.error_rate > thresholds['error_rate_threshold'] * 2 else AlertSeverity.MEDIUM
            await self._create_alert(
                severity,
                f"agent_{agent_id}",
                f"High error rate for agent {agent_id}: {metrics.error_rate:.2%}",
                {'agent_id': agent_id, 'error_rate': metrics.error_rate, 'threshold': thresholds['error_rate_threshold']}
            )
        
        # Memory usage alert
        if metrics.memory_usage_mb > thresholds['memory_usage_mb']:
            severity = AlertSeverity.HIGH if metrics.memory_usage_mb > thresholds['memory_usage_mb'] * 1.5 else AlertSeverity.MEDIUM
            await self._create_alert(
                severity,
                f"agent_{agent_id}",
                f"High memory usage for agent {agent_id}: {metrics.memory_usage_mb:.1f}MB",
                {'agent_id': agent_id, 'memory_usage': metrics.memory_usage_mb, 'threshold': thresholds['memory_usage_mb']}
            )
    
    async def _check_llm_cost_alerts(self, model: str, metrics: Dict[str, Any]):
        """Check for LLM cost alerts"""
        # Daily cost threshold (configurable)
        daily_cost_threshold = self.monitoring_config.get('daily_cost_threshold', 100.0)
        
        if metrics['total_cost'] > daily_cost_threshold:
            await self._create_alert(
                AlertSeverity.MEDIUM,
                f"llm_{model}",
                f"High LLM cost for model {model}: ${metrics['total_cost']:.2f}",
                {'model': model, 'total_cost': metrics['total_cost'], 'threshold': daily_cost_threshold}
            )
    
    async def _create_alert(self, severity: AlertSeverity, component: str, message: str, details: Dict[str, Any]):
        """Create and process a new alert"""
        alert_id = f"{component}_{int(time.time() * 1000)}"
        
        # Check if similar alert already exists
        for existing_alert in self.active_alerts:
            if existing_alert.component == component and existing_alert.message == message:
                # Update existing alert timestamp
                existing_alert.timestamp = datetime.now()
                return
        
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            component=component,
            message=message,
            details=details,
            timestamp=datetime.now()
        )
        
        self.active_alerts.append(alert)
        logger.warning(f"Alert created: {severity.value} - {component} - {message}")
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    async def _calculate_agent_analytics(self, agent_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate analytics for a specific agent"""
        try:
            analytics = {
                'avg_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'avg_success_rate': 0.0,
                'total_requests': 0,
                'trend_analysis': {}
            }
            
            # Get response time data
            response_times = [
                value for timestamp, value in self.performance_history[f"{agent_id}_response_time"]
                if start_time <= timestamp <= end_time
            ]
            
            if response_times:
                analytics['avg_response_time'] = np.mean(response_times)
                analytics['min_response_time'] = np.min(response_times)
                analytics['max_response_time'] = np.max(response_times)
                analytics['total_requests'] = len(response_times)
                
                # Simple trend analysis
                if len(response_times) > 10:
                    recent_avg = np.mean(response_times[-10:])
                    older_avg = np.mean(response_times[:10])
                    analytics['trend_analysis']['response_time_trend'] = 'improving' if recent_avg < older_avg else 'degrading'
            
            # Get success rate data
            success_rates = [
                value for timestamp, value in self.performance_history[f"{agent_id}_success_rate"]
                if start_time <= timestamp <= end_time
            ]
            
            if success_rates:
                analytics['avg_success_rate'] = np.mean(success_rates)
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating agent analytics for {agent_id}: {e}")
            return {'error': str(e)}
    
    async def _calculate_llm_analytics(self, model: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate analytics for a specific LLM model"""
        try:
            analytics = {
                'total_tokens_used': 0,
                'total_cost': 0.0,
                'avg_tokens_per_request': 0.0,
                'cost_trend': {}
            }
            
            # Get token usage data
            token_data = [
                value for timestamp, value in self.performance_history[f"llm_{model}_tokens"]
                if start_time <= timestamp <= end_time
            ]
            
            if token_data:
                analytics['total_tokens_used'] = sum(token_data)
                analytics['avg_tokens_per_request'] = np.mean(token_data)
            
            # Get cost data
            cost_data = [
                value for timestamp, value in self.performance_history[f"llm_{model}_cost"]
                if start_time <= timestamp <= end_time
            ]
            
            if cost_data:
                analytics['total_cost'] = sum(cost_data)
                
                # Cost trend analysis
                if len(cost_data) > 10:
                    recent_avg = np.mean(cost_data[-10:])
                    older_avg = np.mean(cost_data[:10])
                    analytics['cost_trend']['direction'] = 'increasing' if recent_avg > older_avg else 'decreasing'
                    analytics['cost_trend']['change_percent'] = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error calculating LLM analytics for {model}: {e}")
            return {'error': str(e)}
    
    async def _calculate_system_trends(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate system-wide performance trends"""
        try:
            trends = {
                'overall_performance_trend': 'stable',
                'system_load_trend': 'stable',
                'error_rate_trend': 'stable'
            }
            
            # Aggregate all agent response times
            all_response_times = []
            for agent_id in self.agent_metrics.keys():
                response_times = [
                    value for timestamp, value in self.performance_history[f"{agent_id}_response_time"]
                    if start_time <= timestamp <= end_time
                ]
                all_response_times.extend(response_times)
            
            if len(all_response_times) > 20:
                mid_point = len(all_response_times) // 2
                first_half_avg = np.mean(all_response_times[:mid_point])
                second_half_avg = np.mean(all_response_times[mid_point:])
                
                if second_half_avg > first_half_avg * 1.1:
                    trends['overall_performance_trend'] = 'degrading'
                elif second_half_avg < first_half_avg * 0.9:
                    trends['overall_performance_trend'] = 'improving'
            
            return trends
            
        except Exception as e:
            logger.error(f"Error calculating system trends: {e}")
            return {'error': str(e)}
    
    async def _detect_anomalies(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Detect performance anomalies using statistical analysis"""
        try:
            anomalies = []
            sensitivity = self.monitoring_config['anomaly_detection']['sensitivity']
            min_data_points = self.monitoring_config['anomaly_detection']['min_data_points']
            
            # Check each agent for response time anomalies
            for agent_id in self.agent_metrics.keys():
                response_times = [
                    value for timestamp, value in self.performance_history[f"{agent_id}_response_time"]
                    if start_time <= timestamp <= end_time
                ]
                
                if len(response_times) >= min_data_points:
                    # Simple statistical anomaly detection
                    mean_rt = np.mean(response_times)
                    std_rt = np.std(response_times)
                    threshold = mean_rt + (sensitivity * std_rt)
                    
                    anomalous_values = [rt for rt in response_times if rt > threshold]
                    
                    if anomalous_values:
                        anomalies.append({
                            'type': 'response_time_anomaly',
                            'agent_id': agent_id,
                            'anomalous_values': len(anomalous_values),
                            'threshold': threshold,
                            'max_value': max(anomalous_values),
                            'description': f"Agent {agent_id} had {len(anomalous_values)} response time anomalies"
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return [] 