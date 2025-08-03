"""
Performance Integration Module

Comprehensive performance integration system for
Phase 6: Market Data & Performance Integration.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
import json

from .market_data_analytics import (
    MarketDataAnalytics, DataQualityMetrics, MarketDataPerformance,
    MarketDataAnalyticsConfig
)
from .data_quality_monitor import (
    DataQualityMonitor, QualityAlert, AlertLevel, MonitoringStatus,
    DataQualityMonitorConfig
)

logger = logging.getLogger(__name__)


class IntegrationStatus(Enum):
    """Integration status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    INITIALIZING = "initializing"


class PerformanceMetric(Enum):
    """Performance metric enumeration"""
    DATA_QUALITY = "data_quality"
    PROCESSING_PERFORMANCE = "processing_performance"
    SYSTEM_PERFORMANCE = "system_performance"
    INTEGRATION_PERFORMANCE = "integration_performance"
    OVERALL_PERFORMANCE = "overall_performance"


@dataclass
class PerformanceSnapshot:
    """Performance snapshot for a specific time period"""
    
    # Basic info
    timestamp: datetime
    symbol: str
    period_minutes: int
    
    # Performance metrics
    data_quality_score: float
    processing_performance_score: float
    system_performance_score: float
    integration_performance_score: float
    overall_performance_score: float
    
    # Detailed metrics
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    system_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Alert information
    active_alerts_count: int = 0
    critical_alerts_count: int = 0
    warning_alerts_count: int = 0
    
    # Integration status
    integration_status: str = "active"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'period_minutes': self.period_minutes,
            'data_quality_score': self.data_quality_score,
            'processing_performance_score': self.processing_performance_score,
            'system_performance_score': self.system_performance_score,
            'integration_performance_score': self.integration_performance_score,
            'overall_performance_score': self.overall_performance_score,
            'quality_metrics': self.quality_metrics,
            'performance_metrics': self.performance_metrics,
            'system_metrics': self.system_metrics,
            'active_alerts_count': self.active_alerts_count,
            'critical_alerts_count': self.critical_alerts_count,
            'warning_alerts_count': self.warning_alerts_count,
            'integration_status': self.integration_status
        }


@dataclass
class PerformanceIntegrationConfig:
    """Configuration for performance integration"""
    
    # Integration settings
    integration_interval_seconds: int = 60
    snapshot_retention_hours: int = 24
    max_snapshots_per_symbol: int = 1440  # 24 hours worth of minute snapshots
    
    # Performance thresholds
    min_quality_score: float = 80.0
    min_performance_score: float = 80.0
    min_overall_score: float = 75.0
    
    # Alert settings
    enable_performance_alerts: bool = True
    performance_alert_threshold: float = 70.0
    critical_performance_threshold: float = 60.0
    
    # Integration features
    enable_real_time_monitoring: bool = True
    enable_historical_analysis: bool = True
    enable_performance_optimization: bool = True
    enable_auto_scaling: bool = False
    
    # Reporting settings
    enable_performance_reports: bool = True
    report_interval_minutes: int = 15
    enable_detailed_logging: bool = True


class PerformanceIntegration:
    """
    Performance Integration System
    
    Provides comprehensive performance integration capabilities that tie together
    MarketDataAnalytics and DataQualityMonitor systems for unified performance management.
    """
    
    def __init__(self, config: Optional[PerformanceIntegrationConfig] = None):
        """
        Initialize Performance Integration
        
        Args:
            config: Configuration for integration system
        """
        self.config = config or PerformanceIntegrationConfig()
        
        # Initialize status
        self.status = IntegrationStatus.INITIALIZING
        
        # Initialize analytics system
        analytics_config = MarketDataAnalyticsConfig(
            monitoring_interval_seconds=self.config.integration_interval_seconds
        )
        self.analytics = MarketDataAnalytics(analytics_config)
        
        # Initialize quality monitor
        monitor_config = DataQualityMonitorConfig(
            monitoring_interval_seconds=self.config.integration_interval_seconds,
            enable_analytics_integration=True
        )
        self.quality_monitor = DataQualityMonitor(monitor_config)
        
        # Performance tracking
        self.performance_snapshots: Dict[str, List[PerformanceSnapshot]] = {}
        self.integration_task: Optional[asyncio.Task] = None
        
        # Symbol tracking
        self.integrated_symbols: Set[str] = set()
        self.symbol_performance_history: Dict[str, List[float]] = {}
        
        # Callback handlers
        self.performance_handlers: List[Callable[[str, PerformanceSnapshot], None]] = []
        self.alert_handlers: List[Callable[[str, QualityAlert], None]] = []
        self.optimization_handlers: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Performance optimization
        self.optimization_history: Dict[str, List[Dict[str, Any]]] = {}
        self.auto_scaling_enabled = self.config.enable_auto_scaling
        
        logger.info("PerformanceIntegration initialized")
    
    async def start_integration(self):
        """Start performance integration"""
        if self.status == IntegrationStatus.ACTIVE:
            logger.warning("Integration already active")
            return
        
        self.status = IntegrationStatus.INITIALIZING
        
        try:
            # Start analytics monitoring
            await self.analytics.start_monitoring()
            
            # Start quality monitoring
            await self.quality_monitor.start_monitoring()
            
            # Start integration task
            self.integration_task = asyncio.create_task(self._integration_loop())
            
            self.status = IntegrationStatus.ACTIVE
            logger.info("Performance integration started")
            
        except Exception as e:
            self.status = IntegrationStatus.ERROR
            logger.error(f"Failed to start performance integration: {e}")
            raise
    
    async def stop_integration(self):
        """Stop performance integration"""
        if self.status == IntegrationStatus.STOPPED:
            logger.warning("Integration already stopped")
            return
        
        self.status = IntegrationStatus.STOPPED
        
        # Stop integration task
        if self.integration_task:
            self.integration_task.cancel()
            try:
                await self.integration_task
            except asyncio.CancelledError:
                pass
        
        # Stop monitoring systems
        await self.analytics.stop_monitoring()
        await self.quality_monitor.stop_monitoring()
        
        logger.info("Performance integration stopped")
    
    async def pause_integration(self):
        """Pause performance integration"""
        if self.status != IntegrationStatus.ACTIVE:
            logger.warning("Integration not active, cannot pause")
            return
        
        self.status = IntegrationStatus.PAUSED
        logger.info("Performance integration paused")
    
    async def resume_integration(self):
        """Resume performance integration"""
        if self.status != IntegrationStatus.PAUSED:
            logger.warning("Integration not paused, cannot resume")
            return
        
        self.status = IntegrationStatus.ACTIVE
        logger.info("Performance integration resumed")
    
    def add_symbol(self, symbol: str):
        """Add symbol to performance integration"""
        self.integrated_symbols.add(symbol)
        self.performance_snapshots[symbol] = []
        self.symbol_performance_history[symbol] = []
        self.optimization_history[symbol] = []
        
        # Add to monitoring systems
        self.quality_monitor.add_symbol(symbol)
        
        logger.info(f"Added {symbol} to performance integration")
    
    def remove_symbol(self, symbol: str):
        """Remove symbol from performance integration"""
        self.integrated_symbols.discard(symbol)
        self.performance_snapshots.pop(symbol, None)
        self.symbol_performance_history.pop(symbol, None)
        self.optimization_history.pop(symbol, None)
        
        # Remove from monitoring systems
        self.quality_monitor.remove_symbol(symbol)
        
        logger.info(f"Removed {symbol} from performance integration")
    
    async def process_market_data(self, symbol: str, market_data: pd.DataFrame, 
                                processing_time: float = 0.0):
        """
        Process market data through the integrated system
        
        Args:
            symbol: Symbol being processed
            market_data: Market data DataFrame
            processing_time: Time taken to process data
        """
        if symbol not in self.integrated_symbols:
            return
        
        try:
            # Process through quality monitor
            await self.quality_monitor.process_market_data(symbol, market_data, processing_time)
            
            # Generate performance snapshot
            snapshot = await self._generate_performance_snapshot(symbol, market_data, processing_time)
            
            # Store snapshot
            self.performance_snapshots[symbol].append(snapshot)
            self.symbol_performance_history[symbol].append(snapshot.overall_performance_score)
            
            # Clean up old snapshots
            self._cleanup_old_snapshots(symbol)
            
            # Check for performance alerts
            if self.config.enable_performance_alerts:
                await self._check_performance_alerts(symbol, snapshot)
            
            # Trigger performance optimization if enabled
            if self.config.enable_performance_optimization:
                await self._trigger_performance_optimization(symbol, snapshot)
            
            # Trigger handlers
            for handler in self.performance_handlers:
                try:
                    handler(symbol, snapshot)
                except Exception as e:
                    logger.error(f"Error in performance handler: {e}")
            
            logger.debug(f"Processed market data for {symbol}: overall_score={snapshot.overall_performance_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error processing market data for {symbol}: {e}")
    
    def add_performance_handler(self, handler: Callable[[str, PerformanceSnapshot], None]):
        """Add performance snapshot handler"""
        self.performance_handlers.append(handler)
        logger.info("Added performance handler")
    
    def add_alert_handler(self, handler: Callable[[str, QualityAlert], None]):
        """Add alert handler"""
        self.alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def add_optimization_handler(self, handler: Callable[[str, Dict[str, Any]], None]):
        """Add optimization handler"""
        self.optimization_handlers.append(handler)
        logger.info("Added optimization handler")
    
    def get_performance_snapshots(self, symbol: str, hours: int = 24) -> List[PerformanceSnapshot]:
        """Get performance snapshots for a symbol"""
        if symbol not in self.performance_snapshots:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        snapshots = self.performance_snapshots[symbol]
        
        return [s for s in snapshots if s.timestamp > cutoff_time]
    
    def get_performance_summary(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for a symbol"""
        snapshots = self.get_performance_snapshots(symbol, hours)
        
        if not snapshots:
            return {"error": f"No performance data available for {symbol}"}
        
        # Calculate summary statistics
        overall_scores = [s.overall_performance_score for s in snapshots]
        quality_scores = [s.data_quality_score for s in snapshots]
        performance_scores = [s.processing_performance_score for s in snapshots]
        
        summary = {
            'symbol': symbol,
            'period_hours': hours,
            'snapshot_count': len(snapshots),
            'avg_overall_score': np.mean(overall_scores),
            'avg_quality_score': np.mean(quality_scores),
            'avg_performance_score': np.mean(performance_scores),
            'min_overall_score': np.min(overall_scores),
            'max_overall_score': np.max(overall_scores),
            'overall_score_std': np.std(overall_scores),
            'performance_trend': self._calculate_performance_trend(overall_scores),
            'latest_snapshot': snapshots[-1].to_dict() if snapshots else None
        }
        
        return summary
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'status': self.status.value,
            'integrated_symbols': list(self.integrated_symbols),
            'analytics_status': 'active' if self.analytics.monitoring_active else 'inactive',
            'quality_monitor_status': self.quality_monitor.status.value,
            'active_alerts_count': len(self.quality_monitor.get_active_alerts()),
            'total_snapshots': sum(len(snapshots) for snapshots in self.performance_snapshots.values()),
            'auto_scaling_enabled': self.auto_scaling_enabled
        }
    
    def generate_integration_report(self, symbol: str, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive integration report"""
        # Get performance summary
        performance_summary = self.get_performance_summary(symbol, hours)
        
        # Get quality monitor report
        monitoring_report = self.quality_monitor.generate_monitoring_report(symbol, hours // 24)
        
        # Get analytics report
        analytics_report = self.analytics.generate_analytics_report(symbol, hours // 24)
        
        # Combine reports
        integration_report = {
            'symbol': symbol,
            'report_period_hours': hours,
            'generated_at': datetime.now().isoformat(),
            'integration_status': self.get_integration_status(),
            'performance_summary': performance_summary,
            'monitoring_report': monitoring_report,
            'analytics_report': analytics_report,
            'optimization_history': self.optimization_history.get(symbol, []),
            'recommendations': self._generate_recommendations(symbol, performance_summary, monitoring_report)
        }
        
        return integration_report
    
    def enable_auto_scaling(self, enabled: bool = True):
        """Enable or disable auto-scaling"""
        self.auto_scaling_enabled = enabled
        logger.info(f"Auto-scaling {'enabled' if enabled else 'disabled'}")
    
    def get_optimization_history(self, symbol: str) -> List[Dict[str, Any]]:
        """Get optimization history for a symbol"""
        return self.optimization_history.get(symbol, [])
    
    # Private helper methods
    
    async def _integration_loop(self):
        """Main integration loop"""
        while self.status == IntegrationStatus.ACTIVE:
            try:
                # Perform integration cycle
                await self._perform_integration_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.config.integration_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                self.status = IntegrationStatus.ERROR
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _perform_integration_cycle(self):
        """Perform one integration cycle"""
        logger.debug("Performing integration cycle")
        
        # Update integration status
        for symbol in self.integrated_symbols:
            # Check if we have recent snapshots
            recent_snapshots = self.get_performance_snapshots(symbol, hours=1)
            
            if recent_snapshots:
                latest_snapshot = recent_snapshots[-1]
                
                # Update integration status based on performance
                if latest_snapshot.overall_performance_score < self.config.critical_performance_threshold:
                    latest_snapshot.integration_status = "critical"
                elif latest_snapshot.overall_performance_score < self.config.performance_alert_threshold:
                    latest_snapshot.integration_status = "warning"
                else:
                    latest_snapshot.integration_status = "healthy"
        
        # Perform auto-scaling if enabled
        if self.auto_scaling_enabled:
            await self._perform_auto_scaling()
    
    async def _generate_performance_snapshot(self, symbol: str, market_data: pd.DataFrame, 
                                           processing_time: float) -> PerformanceSnapshot:
        """Generate performance snapshot"""
        # Get quality metrics from analytics
        quality_metrics = await self.analytics.analyze_data_quality(market_data, symbol)
        performance_metrics = await self.analytics.analyze_performance(market_data, processing_time)
        
        # Calculate scores
        data_quality_score = quality_metrics.overall_quality_score
        processing_performance_score = performance_metrics.overall_performance_score
        
        # Calculate system performance score (mock implementation)
        system_performance_score = self._calculate_system_performance_score()
        
        # Calculate integration performance score
        integration_performance_score = self._calculate_integration_performance_score(
            data_quality_score, processing_performance_score, system_performance_score
        )
        
        # Calculate overall performance score
        overall_performance_score = self._calculate_overall_performance_score(
            data_quality_score, processing_performance_score, 
            system_performance_score, integration_performance_score
        )
        
        # Get alert counts
        active_alerts = self.quality_monitor.get_active_alerts(symbol)
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in active_alerts if a.level == AlertLevel.WARNING]
        
        # Create snapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            symbol=symbol,
            period_minutes=1,
            data_quality_score=data_quality_score,
            processing_performance_score=processing_performance_score,
            system_performance_score=system_performance_score,
            integration_performance_score=integration_performance_score,
            overall_performance_score=overall_performance_score,
            quality_metrics=quality_metrics.to_dict(),
            performance_metrics=performance_metrics.to_dict(),
            system_metrics=self._get_system_metrics(),
            active_alerts_count=len(active_alerts),
            critical_alerts_count=len(critical_alerts),
            warning_alerts_count=len(warning_alerts),
            integration_status="active"
        )
        
        return snapshot
    
    def _calculate_system_performance_score(self) -> float:
        """Calculate system performance score (mock implementation)"""
        # In a real system, this would check actual system metrics
        # For now, return a mock score based on time of day
        hour = datetime.now().hour
        if 9 <= hour <= 16:  # Market hours
            return 85.0
        else:
            return 95.0
    
    def _calculate_integration_performance_score(self, quality_score: float, 
                                               performance_score: float, 
                                               system_score: float) -> float:
        """Calculate integration performance score"""
        # Weighted average of component scores
        weights = [0.4, 0.4, 0.2]  # Quality, Performance, System
        scores = [quality_score, performance_score, system_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _calculate_overall_performance_score(self, quality_score: float, 
                                           performance_score: float, 
                                           system_score: float, 
                                           integration_score: float) -> float:
        """Calculate overall performance score"""
        # Weighted average of all scores
        weights = [0.3, 0.3, 0.2, 0.2]  # Quality, Performance, System, Integration
        scores = [quality_score, performance_score, system_score, integration_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get system metrics (mock implementation)"""
        return {
            'memory_usage_mb': 512.0,
            'cpu_usage_percent': 25.0,
            'disk_usage_percent': 60.0,
            'network_latency_ms': 50.0,
            'active_connections': 100
        }
    
    def _cleanup_old_snapshots(self, symbol: str):
        """Clean up old performance snapshots"""
        if symbol not in self.performance_snapshots:
            return
        
        snapshots = self.performance_snapshots[symbol]
        cutoff_time = datetime.now() - timedelta(hours=self.config.snapshot_retention_hours)
        
        # Remove old snapshots
        self.performance_snapshots[symbol] = [
            s for s in snapshots if s.timestamp > cutoff_time
        ]
        
        # Limit number of snapshots
        if len(self.performance_snapshots[symbol]) > self.config.max_snapshots_per_symbol:
            self.performance_snapshots[symbol] = self.performance_snapshots[symbol][-self.config.max_snapshots_per_symbol:]
    
    async def _check_performance_alerts(self, symbol: str, snapshot: PerformanceSnapshot):
        """Check for performance alerts"""
        # Check overall performance score
        if snapshot.overall_performance_score < self.config.critical_performance_threshold:
            await self._create_performance_alert(
                symbol, "overall_performance_score", snapshot.overall_performance_score,
                self.config.critical_performance_threshold, AlertLevel.CRITICAL
            )
        elif snapshot.overall_performance_score < self.config.performance_alert_threshold:
            await self._create_performance_alert(
                symbol, "overall_performance_score", snapshot.overall_performance_score,
                self.config.performance_alert_threshold, AlertLevel.WARNING
            )
        
        # Check individual component scores
        if snapshot.data_quality_score < self.config.min_quality_score:
            await self._create_performance_alert(
                symbol, "data_quality_score", snapshot.data_quality_score,
                self.config.min_quality_score, AlertLevel.WARNING
            )
        
        if snapshot.processing_performance_score < self.config.min_performance_score:
            await self._create_performance_alert(
                symbol, "processing_performance_score", snapshot.processing_performance_score,
                self.config.min_performance_score, AlertLevel.WARNING
            )
    
    async def _create_performance_alert(self, symbol: str, metric_name: str, current_value: float,
                                      threshold_value: float, level: AlertLevel):
        """Create performance alert"""
        alert_id = f"performance_{symbol}_{metric_name}_{datetime.now().timestamp()}"
        
        # Create alert using quality monitor
        alert = QualityAlert(
            alert_id=alert_id,
            level=level,
            message=f"Performance {metric_name} for {symbol} is {current_value:.2f} (threshold: {threshold_value:.2f})",
            symbol=symbol,
            timestamp=datetime.now(),
            metric_name=metric_name,
            current_value=current_value,
            threshold_value=threshold_value,
            severity_score=1.0 - (current_value / 100.0)
        )
        
        # Trigger alert handlers
        for handler in self.alert_handlers:
            try:
                handler(symbol, alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
        
        logger.warning(f"Performance alert created: {alert.message}")
    
    async def _trigger_performance_optimization(self, symbol: str, snapshot: PerformanceSnapshot):
        """Trigger performance optimization"""
        # Check if optimization is needed
        if snapshot.overall_performance_score < self.config.min_overall_score:
            optimization_suggestions = self._generate_optimization_suggestions(symbol, snapshot)
            
            if optimization_suggestions:
                # Store optimization record
                optimization_record = {
                    'timestamp': datetime.now().isoformat(),
                    'trigger_score': snapshot.overall_performance_score,
                    'suggestions': optimization_suggestions,
                    'snapshot': snapshot.to_dict()
                }
                
                self.optimization_history[symbol].append(optimization_record)
                
                # Trigger optimization handlers
                for handler in self.optimization_handlers:
                    try:
                        handler(symbol, optimization_record)
                    except Exception as e:
                        logger.error(f"Error in optimization handler: {e}")
                
                logger.info(f"Performance optimization triggered for {symbol}")
    
    def _generate_optimization_suggestions(self, symbol: str, snapshot: PerformanceSnapshot) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        
        # Quality-based suggestions
        if snapshot.data_quality_score < 80:
            suggestions.append("Consider implementing data validation checks")
            suggestions.append("Review data source reliability")
        
        if snapshot.data_quality_score < 90:
            suggestions.append("Optimize data preprocessing pipeline")
        
        # Performance-based suggestions
        if snapshot.processing_performance_score < 80:
            suggestions.append("Optimize data processing algorithms")
            suggestions.append("Consider parallel processing")
        
        if snapshot.processing_performance_score < 90:
            suggestions.append("Review processing pipeline efficiency")
        
        # System-based suggestions
        if snapshot.system_performance_score < 80:
            suggestions.append("Consider scaling system resources")
            suggestions.append("Review system configuration")
        
        # Integration-based suggestions
        if snapshot.integration_performance_score < 80:
            suggestions.append("Review integration pipeline")
            suggestions.append("Optimize inter-module communication")
        
        return suggestions
    
    async def _perform_auto_scaling(self):
        """Perform auto-scaling based on performance metrics"""
        if not self.auto_scaling_enabled:
            return
        
        for symbol in self.integrated_symbols:
            recent_snapshots = self.get_performance_snapshots(symbol, hours=1)
            
            if recent_snapshots:
                avg_score = np.mean([s.overall_performance_score for s in recent_snapshots])
                
                # Auto-scaling logic (mock implementation)
                if avg_score < 70:
                    logger.info(f"Auto-scaling triggered for {symbol} (score: {avg_score:.2f})")
                    # In a real system, this would trigger actual scaling actions
                elif avg_score > 95:
                    logger.info(f"Auto-scaling down for {symbol} (score: {avg_score:.2f})")
                    # In a real system, this would trigger scaling down
    
    def _calculate_performance_trend(self, scores: List[float]) -> str:
        """Calculate performance trend"""
        if len(scores) < 2:
            return "insufficient_data"
        
        # Calculate trend using linear regression
        x = np.arange(len(scores))
        trend = np.polyfit(x, scores, 1)[0]
        
        if trend > 1.0:
            return "improving"
        elif trend < -1.0:
            return "declining"
        else:
            return "stable"
    
    def _generate_recommendations(self, symbol: str, performance_summary: Dict[str, Any], 
                                monitoring_report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on performance and monitoring data"""
        recommendations = []
        
        # Performance-based recommendations
        avg_overall_score = performance_summary.get('avg_overall_score', 0)
        if avg_overall_score < 80:
            recommendations.append("Consider performance optimization")
        if avg_overall_score < 90:
            recommendations.append("Monitor performance trends closely")
        
        # Quality-based recommendations
        if 'analytics_report' in monitoring_report:
            analytics_report = monitoring_report['analytics_report']
            quality_score = analytics_report.get('overall_health_score', 0)
            
            if quality_score < 80:
                recommendations.append("Review data quality processes")
            if quality_score < 90:
                recommendations.append("Implement additional quality checks")
        
        # Alert-based recommendations
        active_alerts_count = monitoring_report.get('active_alerts_count', 0)
        if active_alerts_count > 5:
            recommendations.append("Address active alerts promptly")
        if active_alerts_count > 10:
            recommendations.append("Review system configuration")
        
        if not recommendations:
            recommendations.append("System performing well - continue monitoring")
        
        return recommendations
    
    def clear_history(self, symbol: Optional[str] = None, hours: Optional[int] = None):
        """Clear historical data"""
        if symbol is None:
            # Clear all symbols
            self.performance_snapshots.clear()
            self.symbol_performance_history.clear()
            self.optimization_history.clear()
        else:
            # Clear specific symbol
            if hours is None:
                # Clear all data for symbol
                self.performance_snapshots.pop(symbol, None)
                self.symbol_performance_history.pop(symbol, None)
                self.optimization_history.pop(symbol, None)
            else:
                # Clear data older than specified hours
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
                if symbol in self.performance_snapshots:
                    self.performance_snapshots[symbol] = [
                        s for s in self.performance_snapshots[symbol]
                        if s.timestamp > cutoff_time
                    ]
        
        logger.info(f"Cleared historical data for {symbol or 'all symbols'} (hours: {hours or 'all'})") 