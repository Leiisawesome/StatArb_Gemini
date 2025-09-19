"""
Risk Management - Enhanced Risk Manager
Comprehensive risk management system integrating all risk components
"""

import logging
import threading
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Callable
from dataclasses import dataclass, field
import time
from collections import defaultdict, deque
import json

# Import risk components
from .exposure_calculator import ExposureCalculator, ExposureType, ExposureBreakdown
from .var_calculator import VarCalculator, VarMethod, RiskMetrics
from .stress_tester import StressTester, StressTestType, PortfolioStressResult
from .limit_monitor import LimitMonitor, RiskLimit, LimitBreach, AlertSeverity
from .correlation_analyzer import CorrelationAnalyzer, CorrelationMethod, CorrelationMatrix

logger = logging.getLogger(__name__)


@dataclass
class RiskSnapshot:
    """Comprehensive risk snapshot"""
    timestamp: datetime
    portfolio_value: float
    exposures: Dict[ExposureType, ExposureBreakdown]
    risk_metrics: RiskMetrics
    correlation_matrix: CorrelationMatrix
    stress_test_results: Dict[str, PortfolioStressResult]
    limit_breaches: List[LimitBreach]
    regime_status: str
    risk_score: float  # Overall risk score 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAlert:
    """Risk alert notification"""
    alert_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class EnhancedRiskManager:
    """
    Enhanced risk management system
    
    Integrates exposure calculation, VaR analysis, stress testing,
    limit monitoring, and correlation analysis into a unified framework.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced risk manager"""
        self.config = config or {}
        self._lock = threading.Lock()
        
        # Initialize risk components
        self.exposure_calculator = ExposureCalculator(config.get('exposure_config', {}))
        self.var_calculator = VarCalculator(config.get('var_config', {}))
        self.stress_tester = StressTester(config.get('stress_config', {}))
        self.limit_monitor = LimitMonitor(config.get('limit_config', {}))
        self.correlation_analyzer = CorrelationAnalyzer(config.get('correlation_config', {}))
        
        # Risk snapshots and alerts
        self._risk_snapshots = deque(maxlen=1000)
        self._risk_alerts = deque(maxlen=1000)
        self._alert_handlers = []
        
        # Configuration
        self.risk_calculation_interval = self.config.get('calculation_interval_seconds', 300)  # 5 minutes
        self.snapshot_retention_days = self.config.get('snapshot_retention_days', 30)
        self.enable_real_time_monitoring = self.config.get('enable_real_time_monitoring', True)
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task = None
        
        # Risk scoring weights
        self.risk_weights = self.config.get('risk_weights', {
            'var': 0.25,
            'stress_test': 0.25,
            'correlation': 0.20,
            'concentration': 0.15,
            'limits': 0.15
        })
        
        # Setup limit monitor alert handler
        self.limit_monitor.add_alert_handler(self._handle_limit_alert)
        
        logger.info("EnhancedRiskManager initialized")
    
    async def calculate_comprehensive_risk(
        self,
        positions: Dict[str, Any],
        portfolio_value: float,
        returns_data: Optional[pd.DataFrame] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> RiskSnapshot:
        """
        Calculate comprehensive risk assessment
        
        Args:
            positions: Current portfolio positions
            portfolio_value: Total portfolio value
            returns_data: Historical returns for analysis
            market_data: Current market data
            
        Returns:
            Comprehensive risk snapshot
        """
        start_time = time.time()
        
        try:
            # Prepare portfolio data for components
            portfolio_data = {
                'total_value': portfolio_value,
                'positions': positions,
                'market_data': market_data or {}
            }
            
            # Calculate exposures
            logger.debug("Calculating exposures...")
            exposures = await self.exposure_calculator.calculate_exposures(
                positions, portfolio_value
            )
            
            # Calculate VaR and risk metrics
            risk_metrics = None
            if returns_data is not None and len(returns_data) > 0:
                logger.debug("Calculating risk metrics...")
                risk_metrics = await self.var_calculator.calculate_comprehensive_risk_metrics(
                    returns_data
                )
            
            # Calculate correlation matrix
            correlation_matrix = None
            if returns_data is not None and len(returns_data.columns) > 1:
                logger.debug("Calculating correlation matrix...")
                correlation_matrix = await self.correlation_analyzer.calculate_correlation_matrix(
                    returns_data
                )
            
            # Run stress tests
            logger.debug("Running stress tests...")
            stress_results = await self._run_key_stress_tests(positions, portfolio_value)
            
            # Check risk limits
            logger.debug("Checking risk limits...")
            limit_breaches = await self.limit_monitor.check_limits(
                portfolio_data, positions, market_data
            )
            
            # Detect correlation regime
            regime_status = "NORMAL"
            if correlation_matrix is not None:
                regime_result = await self.correlation_analyzer.detect_correlation_regime(
                    correlation_matrix.matrix, returns_data
                )
                regime_status = regime_result.current_regime.value.upper()
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(
                exposures, risk_metrics, stress_results, limit_breaches, regime_status
            )
            
            # Create risk snapshot
            snapshot = RiskSnapshot(
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                exposures=exposures,
                risk_metrics=risk_metrics,
                correlation_matrix=correlation_matrix,
                stress_test_results=stress_results,
                limit_breaches=limit_breaches,
                regime_status=regime_status,
                risk_score=risk_score,
                metadata={
                    'calculation_time': time.time() - start_time,
                    'positions_count': len(positions),
                    'returns_data_available': returns_data is not None
                }
            )
            
            # Store snapshot
            self._store_risk_snapshot(snapshot)
            
            # Generate alerts for high risk situations
            await self._check_risk_alerts(snapshot)
            
            logger.info(f"Comprehensive risk calculation completed in {time.time() - start_time:.3f}s - Risk Score: {risk_score:.1f}")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive risk: {e}")
            raise
    
    async def _run_key_stress_tests(
        self,
        positions: Dict[str, Any],
        portfolio_value: float
    ) -> Dict[str, PortfolioStressResult]:
        """Run key stress test scenarios"""
        
        stress_results = {}
        
        # Key scenarios to run
        key_scenarios = [
            'financial_crisis_2008',
            'covid_pandemic_2020',
            'rate_shock',
            'geopolitical_crisis'
        ]
        
        for scenario_name in key_scenarios:
            try:
                result = await self.stress_tester.run_stress_test(
                    scenario_name, positions, portfolio_value
                )
                stress_results[scenario_name] = result
            except Exception as e:
                logger.warning(f"Failed to run stress test {scenario_name}: {e}")
        
        return stress_results
    
    def _calculate_risk_score(
        self,
        exposures: Dict[ExposureType, ExposureBreakdown],
        risk_metrics: Optional[RiskMetrics],
        stress_results: Dict[str, PortfolioStressResult],
        limit_breaches: List[LimitBreach],
        regime_status: str
    ) -> float:
        """Calculate overall risk score (0-100, higher = more risky)"""
        
        total_score = 0.0
        
        # VaR component
        if risk_metrics:
            var_99 = risk_metrics.var_1d.get(0.99, 0)
            var_score = min(100, abs(var_99) * 10)  # Normalize to 0-100
            total_score += var_score * self.risk_weights.get('var', 0.25)
        
        # Stress test component
        if stress_results:
            worst_stress_pnl = min([result.total_pnl_percentage for result in stress_results.values()])
            stress_score = min(100, abs(worst_stress_pnl))
            total_score += stress_score * self.risk_weights.get('stress_test', 0.25)
        
        # Correlation/regime component
        regime_scores = {'LOW': 20, 'NORMAL': 40, 'HIGH': 70, 'CRISIS': 100}
        regime_score = regime_scores.get(regime_status, 40)
        total_score += regime_score * self.risk_weights.get('correlation', 0.20)
        
        # Concentration component
        if ExposureType.SINGLE_NAME in exposures:
            single_name_exposures = exposures[ExposureType.SINGLE_NAME].exposures
            if single_name_exposures:
                max_concentration = max([abs(exp.percentage) for exp in single_name_exposures])
                concentration_score = min(100, max_concentration * 2)  # 50% = 100 score
                total_score += concentration_score * self.risk_weights.get('concentration', 0.15)
        
        # Limit breach component
        if limit_breaches:
            critical_breaches = sum(1 for breach in limit_breaches if breach.severity == AlertSeverity.CRITICAL)
            warning_breaches = sum(1 for breach in limit_breaches if breach.severity == AlertSeverity.WARNING)
            breach_score = min(100, critical_breaches * 50 + warning_breaches * 25)
            total_score += breach_score * self.risk_weights.get('limits', 0.15)
        
        return min(100, max(0, total_score))
    
    def _store_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        """Store risk snapshot and clean up old ones"""
        with self._lock:
            self._risk_snapshots.append(snapshot)
        
        # Clean up old snapshots
        cutoff_time = datetime.now() - timedelta(days=self.snapshot_retention_days)
        
        with self._lock:
            self._risk_snapshots = deque(
                [s for s in self._risk_snapshots if s.timestamp >= cutoff_time],
                maxlen=1000
            )
    
    async def _check_risk_alerts(self, snapshot: RiskSnapshot) -> None:
        """Check for risk alert conditions"""
        
        alerts = []
        
        # High risk score alert
        if snapshot.risk_score > 80:
            alert = RiskAlert(
                alert_id=f"high_risk_{int(time.time())}",
                alert_type="HIGH_RISK_SCORE",
                severity=AlertSeverity.CRITICAL,
                message=f"Portfolio risk score is high: {snapshot.risk_score:.1f}/100",
                details={'risk_score': snapshot.risk_score}
            )
            alerts.append(alert)
        
        # Crisis regime alert
        if snapshot.regime_status == "CRISIS":
            alert = RiskAlert(
                alert_id=f"crisis_regime_{int(time.time())}",
                alert_type="CRISIS_REGIME",
                severity=AlertSeverity.CRITICAL,
                message="Portfolio correlation regime indicates crisis conditions",
                details={'regime': snapshot.regime_status}
            )
            alerts.append(alert)
        
        # Extreme stress test results
        for scenario_name, result in snapshot.stress_test_results.items():
            if result.total_pnl_percentage < -20:  # More than 20% loss
                alert = RiskAlert(
                    alert_id=f"stress_test_{scenario_name}_{int(time.time())}",
                    alert_type="EXTREME_STRESS_LOSS",
                    severity=AlertSeverity.WARNING,
                    message=f"Extreme loss in {scenario_name} stress test: {result.total_pnl_percentage:.1f}%",
                    details={'scenario': scenario_name, 'pnl_percentage': result.total_pnl_percentage}
                )
                alerts.append(alert)
        
        # Store and send alerts
        for alert in alerts:
            await self._send_risk_alert(alert)
    
    async def _handle_limit_alert(self, breach: LimitBreach) -> None:
        """Handle alert from limit monitor"""
        alert = RiskAlert(
            alert_id=f"limit_breach_{breach.limit_id}_{int(time.time())}",
            alert_type="LIMIT_BREACH",
            severity=breach.severity,
            message=f"Risk limit breach: {breach.limit_name}",
            details={
                'limit_id': breach.limit_id,
                'current_value': breach.current_value,
                'threshold': breach.threshold_value,
                'breach_amount': breach.breach_amount
            }
        )
        await self._send_risk_alert(alert)
    
    async def _send_risk_alert(self, alert: RiskAlert) -> None:
        """Send risk alert to registered handlers"""
        
        # Store alert
        with self._lock:
            self._risk_alerts.append(alert)
        
        # Send to handlers
        for handler in self._alert_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error sending risk alert: {e}")
    
    def add_alert_handler(self, handler: Callable[[RiskAlert], None]) -> None:
        """Add risk alert handler"""
        self._alert_handlers.append(handler)
        logger.info("Added risk alert handler")
    
    def remove_alert_handler(self, handler: Callable[[RiskAlert], None]) -> None:
        """Remove risk alert handler"""
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
            logger.info("Removed risk alert handler")
    
    def get_latest_risk_snapshot(self) -> Optional[RiskSnapshot]:
        """Get most recent risk snapshot"""
        with self._lock:
            return self._risk_snapshots[-1] if self._risk_snapshots else None
    
    def get_risk_snapshots(self, hours: int = 24) -> List[RiskSnapshot]:
        """Get risk snapshots from specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [s for s in self._risk_snapshots if s.timestamp >= cutoff_time]
    
    def get_recent_alerts(self, hours: int = 24) -> List[RiskAlert]:
        """Get recent risk alerts"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            return [a for a in self._risk_alerts if a.timestamp >= cutoff_time]
    
    async def add_risk_limit(self, limit: RiskLimit) -> None:
        """Add risk limit"""
        self.limit_monitor.add_limit(limit)
        logger.info(f"Added risk limit: {limit.name}")
    
    async def update_risk_limit(self, limit_id: str, updates: Dict[str, Any]) -> None:
        """Update risk limit"""
        self.limit_monitor.update_limit(limit_id, updates)
        logger.info(f"Updated risk limit: {limit_id}")
    
    async def remove_risk_limit(self, limit_id: str) -> None:
        """Remove risk limit"""
        self.limit_monitor.remove_limit(limit_id)
        logger.info(f"Removed risk limit: {limit_id}")
    
    def get_all_risk_limits(self) -> List[RiskLimit]:
        """Get all risk limits"""
        return self.limit_monitor.get_all_limits()
    
    def get_current_limit_breaches(self) -> List[LimitBreach]:
        """Get current limit breaches"""
        return self.limit_monitor.get_current_breaches()
    
    async def start_monitoring(self, data_provider: Callable[[], Dict[str, Any]]) -> None:
        """Start automated risk monitoring"""
        if self._monitoring_active:
            logger.warning("Risk monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(data_provider))
        logger.info("Started automated risk monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop automated risk monitoring"""
        self._monitoring_active = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped automated risk monitoring")
    
    async def _monitoring_loop(self, data_provider: Callable[[], Dict[str, Any]]) -> None:
        """Main risk monitoring loop"""
        while self._monitoring_active:
            try:
                # Get current data
                data = await data_provider()
                positions = data.get('positions', {})
                portfolio_value = data.get('portfolio_value', 0)
                returns_data = data.get('returns_data')
                market_data = data.get('market_data', {})
                
                # Calculate comprehensive risk
                await self.calculate_comprehensive_risk(
                    positions, portfolio_value, returns_data, market_data
                )
                
                # Wait for next calculation
                await asyncio.sleep(self.risk_calculation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in risk monitoring loop: {e}")
                await asyncio.sleep(self.risk_calculation_interval)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        latest_snapshot = self.get_latest_risk_snapshot()
        
        if not latest_snapshot:
            return {'status': 'No risk data available'}
        
        recent_alerts = self.get_recent_alerts(24)
        
        summary = {
            'timestamp': latest_snapshot.timestamp,
            'portfolio_value': latest_snapshot.portfolio_value,
            'risk_score': latest_snapshot.risk_score,
            'regime_status': latest_snapshot.regime_status,
            'limit_breaches': len(latest_snapshot.limit_breaches),
            'recent_alerts': len(recent_alerts),
            'var_metrics': {
                'var_95': latest_snapshot.risk_metrics.var_1d[0.95] if latest_snapshot.risk_metrics else None,
                'var_99': latest_snapshot.risk_metrics.var_1d[0.99] if latest_snapshot.risk_metrics else None,
                'volatility': latest_snapshot.risk_metrics.volatility_annual if latest_snapshot.risk_metrics else None
            },
            'worst_stress_scenario': self._get_worst_stress_scenario(latest_snapshot.stress_test_results),
            'top_exposures': self._get_top_exposures(latest_snapshot.exposures)
        }
        
        return summary
    
    def _get_worst_stress_scenario(self, stress_results: Dict[str, PortfolioStressResult]) -> Dict[str, Any]:
        """Get worst stress test scenario"""
        if not stress_results:
            return {}
        
        worst_scenario = min(stress_results.values(), key=lambda x: x.total_pnl_percentage)
        
        return {
            'scenario': worst_scenario.scenario_name,
            'pnl_percentage': worst_scenario.total_pnl_percentage,
            'pnl_amount': worst_scenario.total_pnl
        }
    
    def _get_top_exposures(self, exposures: Dict[ExposureType, ExposureBreakdown]) -> List[Dict[str, Any]]:
        """Get top exposures by absolute value"""
        all_exposures = []
        
        for exposure_type, breakdown in exposures.items():
            for exposure_item in breakdown.exposures:
                all_exposures.append({
                    'type': exposure_type.value,
                    'identifier': exposure_item.identifier,
                    'value': exposure_item.value,
                    'percentage': exposure_item.percentage
                })
        
        # Sort by absolute percentage and return top 10
        all_exposures.sort(key=lambda x: abs(x['percentage']), reverse=True)
        return all_exposures[:10]
    
    async def cleanup(self) -> None:
        """Cleanup all risk components"""
        await self.stop_monitoring()
        
        # Cleanup individual components
        await self.exposure_calculator.cleanup()
        await self.var_calculator.cleanup()
        await self.stress_tester.cleanup()
        await self.limit_monitor.cleanup()
        await self.correlation_analyzer.cleanup()
        
        logger.info("EnhancedRiskManager cleanup completed")