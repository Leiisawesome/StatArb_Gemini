"""
Phase 2 Integration: Real-Time Monitoring System
===============================================

This module integrates all Phase 2 components into a unified real-time monitoring system:
- Real-time pair relationship monitoring
- Correlation breakdown detection
- Regime change monitoring
- Performance degradation alerts

The system provides a single interface for comprehensive monitoring with
coordinated alerts and intelligent prioritization.

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

# Import Phase 2 components
from .realtime_monitoring import RealTimeMonitor, MonitoringAlert, RegimeChangeEvent
from .correlation_breakdown_detector import CorrelationBreakdownDetector, BreakdownEvent
from .regime_change_monitor import RegimeChangeMonitor, RegimeChangeEvent as RegimeEvent
from .performance_alert_system import PerformanceAlertSystem, PerformanceAlert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoringComponent(Enum):
    """Monitoring system components"""
    REALTIME_MONITOR = "REALTIME_MONITOR"
    CORRELATION_DETECTOR = "CORRELATION_DETECTOR"
    REGIME_MONITOR = "REGIME_MONITOR"
    PERFORMANCE_ALERTS = "PERFORMANCE_ALERTS"

class SystemStatus(Enum):
    """System status levels"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"
    MAINTENANCE = "MAINTENANCE"

@dataclass
class UnifiedAlert:
    """Unified alert combining all monitoring components"""
    alert_id: str
    pair_id: str
    timestamp: datetime
    component: MonitoringComponent
    priority: str
    alert_type: str
    message: str
    
    # Component-specific data
    component_data: Dict[str, Any]
    
    # Correlation with other alerts
    related_alerts: List[str] = field(default_factory=list)
    
    # Action recommendations
    recommended_actions: List[str] = field(default_factory=list)
    
    # Status
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class MonitoringHealth:
    """Health status of monitoring components"""
    component: MonitoringComponent
    status: SystemStatus
    last_update: datetime
    error_count: int = 0
    uptime: timedelta = field(default_factory=lambda: timedelta(0))
    performance_metrics: Dict[str, float] = field(default_factory=dict)

class Phase2MonitoringSystem:
    """
    Unified Phase 2 Real-Time Monitoring System
    
    This class integrates all Phase 2 monitoring components:
    - Real-time pair relationship monitoring
    - Correlation breakdown detection
    - Regime change monitoring
    - Performance degradation alerts
    
    Provides unified alerting, intelligent prioritization, and coordinated responses.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified monitoring system
        
        Args:
            config: Configuration dictionary for all components
        """
        self.config = config or {}
        
        # Initialize components
        self.realtime_monitor = RealTimeMonitor(
            update_interval=self.config.get('realtime_update_interval', 60),
            correlation_window=self.config.get('correlation_window', 50)
        )
        
        self.correlation_detector = CorrelationBreakdownDetector(
            significance_level=self.config.get('significance_level', 0.05),
            min_observations=self.config.get('min_observations', 30)
        )
        
        self.regime_monitor = RegimeChangeMonitor(
            n_regimes=self.config.get('n_regimes', 5),
            lookback_window=self.config.get('lookback_window', 252)
        )
        
        notification_config = self.config.get('notification_config')
        self.performance_alerts = PerformanceAlertSystem(
            monitoring_window=self.config.get('monitoring_window', 252),
            alert_frequency=self.config.get('alert_frequency', 300),
            notification_config=notification_config if notification_config is not None else {}
        )
        
        # System state
        self.system_status = SystemStatus.HEALTHY
        self.component_health: Dict[MonitoringComponent, MonitoringHealth] = {}
        self.unified_alerts: List[UnifiedAlert] = []
        
        # Alert correlation and prioritization
        self.alert_correlator = AlertCorrelator()
        self.alert_prioritizer = AlertPrioritizer()
        
        # Callbacks
        self.unified_callbacks: List[Callable[[UnifiedAlert], None]] = []
        
        # Threading
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize component callbacks
        self._setup_component_callbacks()
        
        # Initialize health monitoring
        self._initialize_health_monitoring()
        
        logger.info("Phase 2 unified monitoring system initialized")
    
    def _setup_component_callbacks(self):
        """Set up callbacks for all monitoring components"""
        # Real-time monitor callbacks
        self.realtime_monitor.add_alert_callback(self._handle_realtime_alert)
        self.realtime_monitor.add_regime_callback(self._handle_regime_change)
        
        # Correlation detector callbacks
        # (Would add callback method to CorrelationBreakdownDetector)
        
        # Regime monitor callbacks
        self.regime_monitor.add_regime_callback(self._handle_regime_event)
        
        # Performance alerts callbacks
        self.performance_alerts.add_alert_callback(self._handle_performance_alert)
    
    def _initialize_health_monitoring(self):
        """Initialize health monitoring for all components"""
        for component in MonitoringComponent:
            self.component_health[component] = MonitoringHealth(
                component=component,
                status=SystemStatus.HEALTHY,
                last_update=datetime.now()
            )
    
    def _handle_realtime_alert(self, alert: MonitoringAlert):
        """Handle alert from real-time monitor"""
        unified_alert = UnifiedAlert(
            alert_id=f"RT_{alert.alert_id}",
            pair_id=alert.pair_id,
            timestamp=alert.timestamp,
            component=MonitoringComponent.REALTIME_MONITOR,
            priority=alert.severity.value,
            alert_type=alert.alert_type,
            message=alert.message,
            component_data={
                'metrics': alert.metrics,
                'action_required': alert.action_required
            }
        )
        
        self._process_unified_alert(unified_alert)
    
    def _handle_regime_change(self, event: RegimeChangeEvent):
        """Handle regime change event"""
        unified_alert = UnifiedAlert(
            alert_id=f"RC_{event.pair_id}_{int(event.timestamp.timestamp())}",
            pair_id=event.pair_id,
            timestamp=event.timestamp,
            component=MonitoringComponent.REGIME_MONITOR,
            priority="HIGH",
            alert_type="REGIME_CHANGE",
            message=f"Regime change: {event.old_regime.value} -> {event.new_regime.value}",
            component_data={
                'old_regime': event.old_regime.value,
                'new_regime': event.new_regime.value,
                'confidence': event.confidence
            }
        )
        
        self._process_unified_alert(unified_alert)
    
    def _handle_regime_event(self, event: RegimeEvent):
        """Handle regime event from regime monitor"""
        unified_alert = UnifiedAlert(
            alert_id=f"RM_{event.event_id}",
            pair_id=event.pair_id,
            timestamp=event.timestamp,
            component=MonitoringComponent.REGIME_MONITOR,
            priority=event.detection_confidence.value,
            alert_type="REGIME_CHANGE",
            message=f"Regime transition: {event.previous_regime.value} -> {event.new_regime.value}",
            component_data={
                'previous_regime': event.previous_regime.value,
                'new_regime': event.new_regime.value,
                'change_type': event.change_type.value,
                'detection_probability': event.detection_probability,
                'recommended_actions': event.recommended_actions
            }
        )
        
        self._process_unified_alert(unified_alert)
    
    def _handle_performance_alert(self, alert: PerformanceAlert):
        """Handle performance degradation alert"""
        unified_alert = UnifiedAlert(
            alert_id=f"PA_{alert.alert_id}",
            pair_id=alert.pair_id,
            timestamp=alert.timestamp,
            component=MonitoringComponent.PERFORMANCE_ALERTS,
            priority=alert.priority.value,
            alert_type=alert.alert_type,
            message=f"Performance degradation: {alert.metric_affected.value} down {alert.degradation_percentage:.1%}",
            component_data={
                'metric_affected': alert.metric_affected.value,
                'current_value': alert.current_value,
                'historical_average': alert.historical_average,
                'degradation_percentage': alert.degradation_percentage,
                'immediate_actions': alert.immediate_actions,
                'risk_adjustments': alert.risk_adjustments
            }
        )
        
        self._process_unified_alert(unified_alert)
    
    def _process_unified_alert(self, alert: UnifiedAlert):
        """Process unified alert with correlation and prioritization"""
        try:
            # Find related alerts
            related_alerts = self.alert_correlator.find_related_alerts(alert, self.unified_alerts)
            alert.related_alerts = [a.alert_id for a in related_alerts]
            
            # Generate recommendations
            alert.recommended_actions = self.alert_prioritizer.generate_recommendations(alert, related_alerts)
            
            # Add to unified alerts
            self.unified_alerts.append(alert)
            
            # Update system status
            self._update_system_status()
            
            # Trigger callbacks
            for callback in self.unified_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in unified callback: {e}")
            
            logger.info(f"Unified alert processed: {alert.alert_id} - {alert.message}")
            
        except Exception as e:
            logger.error(f"Error processing unified alert: {e}")
    
    def _update_system_status(self):
        """Update overall system status based on active alerts"""
        active_alerts = [a for a in self.unified_alerts if not a.resolved]
        
        if not active_alerts:
            self.system_status = SystemStatus.HEALTHY
        else:
            priorities = [a.priority for a in active_alerts]
            
            if "EMERGENCY" in priorities:
                self.system_status = SystemStatus.EMERGENCY
            elif "CRITICAL" in priorities:
                self.system_status = SystemStatus.CRITICAL
            elif any(p in ["HIGH", "SEVERE"] for p in priorities):
                self.system_status = SystemStatus.WARNING
            else:
                self.system_status = SystemStatus.HEALTHY
    
    def add_pair(self, pair_id: str, symbol1: str, symbol2: str):
        """Add a pair to all monitoring components"""
        self.realtime_monitor.add_pair(pair_id, symbol1, symbol2)
        # Other components will be updated as data flows through
        
        logger.info(f"Added pair {pair_id} to unified monitoring")
    
    def update_pair_data(self, pair_id: str, price1: float, price2: float, 
                        volume1: float = 1.0, volume2: float = 1.0, 
                        timestamp: Optional[datetime] = None):
        """Update price data for all components"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Update real-time monitor
        self.realtime_monitor.update_price_data(pair_id, price1, price2, timestamp)
        
        # Calculate correlation for correlation detector
        # (This would require maintaining price history)
        
        # Update regime monitor
        self.regime_monitor.add_pair_data(pair_id, price1, price2, volume1, volume2, timestamp or datetime.now())
        
        # Update component health
        self._update_component_health(MonitoringComponent.REALTIME_MONITOR)
        self._update_component_health(MonitoringComponent.REGIME_MONITOR)
    
    def add_trade_record(self, pair_id: str, trade_type: str, entry_price: float,
                        exit_price: float, quantity: float, pnl: float,
                        duration: int, timestamp: Optional[datetime] = None):
        """Add trade record for performance monitoring"""
        self.performance_alerts.add_trade_record(
            pair_id, trade_type, entry_price, exit_price, 
            quantity, pnl, duration, timestamp=timestamp or datetime.now()
        )
        
        self._update_component_health(MonitoringComponent.PERFORMANCE_ALERTS)
    
    def _update_component_health(self, component: MonitoringComponent):
        """Update health status of a component"""
        if component in self.component_health:
            health = self.component_health[component]
            health.last_update = datetime.now()
            health.status = SystemStatus.HEALTHY  # Would implement actual health checks
    
    def start_monitoring(self):
        """Start all monitoring components"""
        try:
            # Start individual components
            self.realtime_monitor.start_monitoring()
            self.regime_monitor  # Would start if it had a start method
            self.performance_alerts.start_monitoring()
            
            # Start unified monitoring thread
            self.monitoring_thread = threading.Thread(target=self._unified_monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Phase 2 unified monitoring started")
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
            raise
    
    def stop_monitoring(self):
        """Stop all monitoring components"""
        try:
            # Stop individual components
            self.realtime_monitor.stop_monitoring()
            self.performance_alerts.stop_monitoring()
            
            # Stop unified monitoring
            self.stop_event.set()
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            
            logger.info("Phase 2 unified monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
    
    def _unified_monitoring_loop(self):
        """Unified monitoring loop for system health and coordination"""
        while not self.stop_event.is_set():
            try:
                # Check component health
                self._check_component_health()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Check for alert patterns
                self._analyze_alert_patterns()
                
                # Sleep
                self.stop_event.wait(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in unified monitoring loop: {e}")
                time.sleep(60)
    
    def _check_component_health(self):
        """Check health of all components"""
        current_time = datetime.now()
        
        for component, health in self.component_health.items():
            # Check if component is responding
            time_since_update = current_time - health.last_update
            
            if time_since_update > timedelta(minutes=5):
                health.status = SystemStatus.WARNING
                logger.warning(f"Component {component.value} hasn't updated in {time_since_update}")
            
            if time_since_update > timedelta(minutes=15):
                health.status = SystemStatus.CRITICAL
                logger.error(f"Component {component.value} appears to be down")
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        original_count = len(self.unified_alerts)
        self.unified_alerts = [
            alert for alert in self.unified_alerts
            if not alert.resolved or alert.timestamp > cutoff_time
        ]
        
        cleaned_count = original_count - len(self.unified_alerts)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old alerts")
    
    def _analyze_alert_patterns(self):
        """Analyze patterns in alerts for system insights"""
        try:
            recent_alerts = [
                alert for alert in self.unified_alerts
                if alert.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            if len(recent_alerts) < 5:
                return
            
            # Analyze alert frequency by pair
            pair_alert_counts = {}
            for alert in recent_alerts:
                pair_alert_counts[alert.pair_id] = pair_alert_counts.get(alert.pair_id, 0) + 1
            
            # Identify problematic pairs
            avg_alerts = np.mean(list(pair_alert_counts.values()))
            problematic_pairs = [
                pair_id for pair_id, count in pair_alert_counts.items()
                if count > avg_alerts * 2
            ]
            
            if problematic_pairs:
                logger.warning(f"Pairs with high alert frequency: {problematic_pairs}")
            
            # Analyze alert types
            alert_types = [alert.alert_type for alert in recent_alerts]
            most_common_type = max(set(alert_types), key=alert_types.count)
            
            if alert_types.count(most_common_type) > len(recent_alerts) * 0.5:
                logger.warning(f"High frequency of {most_common_type} alerts")
            
        except Exception as e:
            logger.error(f"Error analyzing alert patterns: {e}")
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary"""
        active_alerts = [a for a in self.unified_alerts if not a.resolved]
        
        return {
            'system_status': self.system_status.value,
            'total_pairs_monitored': len(set(a.pair_id for a in self.unified_alerts)),
            'active_alerts': len(active_alerts),
            'alerts_by_priority': {
                priority: len([a for a in active_alerts if a.priority == priority])
                for priority in set(a.priority for a in active_alerts)
            },
            'alerts_by_component': {
                component.value: len([a for a in active_alerts if a.component == component])
                for component in MonitoringComponent
            },
            'component_health': {
                component.value: {
                    'status': health.status.value,
                    'last_update': health.last_update.isoformat(),
                    'error_count': health.error_count
                }
                for component, health in self.component_health.items()
            },
            'recent_alert_trends': self._get_alert_trends(),
            'last_update': datetime.now().isoformat()
        }
    
    def _get_alert_trends(self) -> Dict[str, Any]:
        """Get alert trends for the summary"""
        recent_alerts = [
            alert for alert in self.unified_alerts
            if alert.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        if not recent_alerts:
            return {}
        
        # Alert frequency by hour
        hourly_counts = {}
        for alert in recent_alerts:
            hour = alert.timestamp.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        return {
            'alerts_last_24h': len(recent_alerts),
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else 0,
            'average_per_hour': len(recent_alerts) / 24,
            'most_active_pairs': self._get_most_active_pairs(recent_alerts)
        }
    
    def _get_most_active_pairs(self, alerts: List[UnifiedAlert]) -> List[Tuple[str, int]]:
        """Get pairs with most alerts"""
        pair_counts = {}
        for alert in alerts:
            pair_counts[alert.pair_id] = pair_counts.get(alert.pair_id, 0) + 1
        
        return sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    def get_pair_status(self, pair_id: str) -> Dict[str, Any]:
        """Get comprehensive status for a specific pair"""
        # Get status from each component
        realtime_status = self.realtime_monitor.get_pair_status(pair_id)
        regime_status = self.regime_monitor.get_current_regime(pair_id)
        
        # Get recent alerts for this pair
        recent_alerts = [
            alert for alert in self.unified_alerts
            if alert.pair_id == pair_id and alert.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            'pair_id': pair_id,
            'realtime_metrics': {
                'correlation': realtime_status.correlation if realtime_status else None,
                'spread_zscore': realtime_status.spread_zscore if realtime_status else None,
                'volatility': realtime_status.volatility if realtime_status else None,
                'last_update': realtime_status.last_update.isoformat() if realtime_status else None
            },
            'regime_status': {
                'current_regime': regime_status.regime_type.value if regime_status else None,
                'confidence': regime_status.confidence.value if regime_status else None,
                'stability': regime_status.stability if regime_status else None,
                'last_update': regime_status.last_update.isoformat() if regime_status else None
            },
            'recent_alerts': len(recent_alerts),
            'alert_breakdown': {
                component.value: len([a for a in recent_alerts if a.component == component])
                for component in MonitoringComponent
            },
            'last_update': datetime.now().isoformat()
        }
    
    def acknowledge_alert(self, alert_id: str, notes: str = ""):
        """Acknowledge a unified alert"""
        for alert in self.unified_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                
                # Acknowledge in source component
                if alert.component == MonitoringComponent.REALTIME_MONITOR:
                    original_id = alert_id.replace("RT_", "")
                    self.realtime_monitor.acknowledge_alert(original_id)
                elif alert.component == MonitoringComponent.PERFORMANCE_ALERTS:
                    original_id = alert_id.replace("PA_", "")
                    self.performance_alerts.acknowledge_alert(original_id, notes)
                
                logger.info(f"Unified alert {alert_id} acknowledged")
                break
    
    def resolve_alert(self, alert_id: str, resolution_notes: str):
        """Resolve a unified alert"""
        for alert in self.unified_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                
                # Resolve in source component
                if alert.component == MonitoringComponent.PERFORMANCE_ALERTS:
                    original_id = alert_id.replace("PA_", "")
                    self.performance_alerts.resolve_alert(original_id, resolution_notes)
                
                logger.info(f"Unified alert {alert_id} resolved: {resolution_notes}")
                break
    
    def add_unified_callback(self, callback: Callable[[UnifiedAlert], None]):
        """Add callback for unified alerts"""
        self.unified_callbacks.append(callback)

class AlertCorrelator:
    """Correlates alerts across different monitoring components"""
    
    def find_related_alerts(self, alert: UnifiedAlert, all_alerts: List[UnifiedAlert]) -> List[UnifiedAlert]:
        """Find alerts related to the given alert"""
        related = []
        
        # Find alerts for the same pair within time window
        time_window = timedelta(minutes=30)
        for other_alert in all_alerts:
            if (other_alert.pair_id == alert.pair_id and
                other_alert.alert_id != alert.alert_id and
                abs(other_alert.timestamp - alert.timestamp) < time_window):
                related.append(other_alert)
        
        return related

class AlertPrioritizer:
    """Prioritizes and generates recommendations for alerts"""
    
    def generate_recommendations(self, alert: UnifiedAlert, related_alerts: List[UnifiedAlert]) -> List[str]:
        """Generate recommendations based on alert and related alerts"""
        recommendations = []
        
        # Base recommendations by component
        if alert.component == MonitoringComponent.REALTIME_MONITOR:
            recommendations.append("Monitor pair closely")
        elif alert.component == MonitoringComponent.CORRELATION_DETECTOR:
            recommendations.append("Review correlation stability")
        elif alert.component == MonitoringComponent.REGIME_MONITOR:
            recommendations.append("Adjust strategy for new regime")
        elif alert.component == MonitoringComponent.PERFORMANCE_ALERTS:
            recommendations.append("Review performance metrics")
        
        # Enhanced recommendations based on related alerts
        if len(related_alerts) > 2:
            recommendations.append("Multiple simultaneous issues - consider halting trading")
        
        # Priority-based recommendations
        if alert.priority in ["CRITICAL", "EMERGENCY"]:
            recommendations.append("Immediate action required")
        
        return recommendations

# Example usage
if __name__ == "__main__":
    # Create unified monitoring system
    monitoring_system = Phase2MonitoringSystem()
    
    # Add callback
    def unified_alert_handler(alert: UnifiedAlert):
        print(f"UNIFIED ALERT: {alert.pair_id} - {alert.component.value} - {alert.priority}")
        print(f"Message: {alert.message}")
        if alert.recommended_actions:
            print(f"Recommendations: {', '.join(alert.recommended_actions)}")
        print("-" * 50)
    
    monitoring_system.add_unified_callback(unified_alert_handler)
    
    # Add pairs
    monitoring_system.add_pair("TSLA_NVDA", "TSLA", "NVDA")
    monitoring_system.add_pair("QQQ_TQQQ", "QQQ", "TQQQ")
    
    # Start monitoring
    monitoring_system.start_monitoring()
    
    # Simulate some data
    import random
    import time
    
    for i in range(20):
        # Update price data
        monitoring_system.update_pair_data(
            "TSLA_NVDA", 
            100 + random.random() * 10, 
            200 + random.random() * 20
        )
        
        # Simulate some trades
        if i % 5 == 0:
            pnl = random.gauss(0.001, 0.01)
            monitoring_system.add_trade_record(
                "TSLA_NVDA", "LONG_SHORT", 100.0, 100.0 + pnl, 1.0, pnl, 60
            )
        
        time.sleep(1)
    
    # Get system summary
    summary = monitoring_system.get_system_summary()
    print("\nSystem Summary:")
    print(json.dumps(summary, indent=2))
    
    # Stop monitoring
    monitoring_system.stop_monitoring() 