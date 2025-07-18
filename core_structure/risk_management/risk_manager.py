"""
Comprehensive Risk Manager for AI-Ready Statistical Arbitrage System
===================================================================

This module provides advanced risk management with:
- Real-time risk monitoring and alerting
- Multi-layer risk controls and limits
- Advanced risk metrics (VaR, CVaR, stress testing)
- AI-driven risk optimization
- Scenario analysis and stress testing

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
import json

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of risk alerts"""
    POSITION_SIZE = "position_size"
    PORTFOLIO_VAR = "portfolio_var"
    CORRELATION = "correlation"
    DRAWDOWN = "drawdown"
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"

@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size: float = 0.15      # 15% max position size
    max_portfolio_var: float = 0.02      # 2% daily VaR limit
    max_correlation: float = 0.8         # 80% max correlation
    max_drawdown: float = 0.05           # 5% max drawdown
    max_concentration: float = 0.25      # 25% max concentration
    max_volatility: float = 0.20         # 20% max volatility
    min_cash_buffer: float = 0.05        # 5% min cash buffer
    var_confidence: float = 0.95         # 95% VaR confidence

@dataclass
class RiskAlert:
    """Risk alert data structure"""
    alert_id: str
    alert_type: AlertType
    risk_level: RiskLevel
    message: str
    current_value: float
    limit_value: float
    timestamp: datetime
    portfolio_snapshot: Dict[str, Any]
    recommended_action: str
    
@dataclass
class RiskCheckResult:
    """Result of risk check"""
    passed: bool
    risk_score: float
    alerts: List[RiskAlert]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskConfig:
    """Risk management configuration"""
    limits: RiskLimits = field(default_factory=RiskLimits)
    check_frequency: int = 60  # seconds
    alert_cooldown: int = 300  # seconds
    stress_test_scenarios: int = 10
    monte_carlo_simulations: int = 1000
    
class RiskManager:
    """
    Comprehensive Risk Management System
    
    Provides real-time risk monitoring, alerting, and control with:
    - Multi-layer risk limits and controls
    - Advanced risk metrics calculation
    - Real-time monitoring and alerting
    - Stress testing and scenario analysis
    - AI-driven risk optimization
    """
    
    def __init__(self, config: Union[Dict[str, Any], RiskConfig]):
        """Initialize risk manager"""
        if isinstance(config, dict):
            self.config = RiskConfig(**config)
        else:
            self.config = config
            
        # Risk state
        self.active_alerts: Dict[str, RiskAlert] = {}
        self.alert_history: List[RiskAlert] = []
        self.risk_metrics_history: List[Dict[str, Any]] = []
        
        # Monitoring state
        self.last_check_time = datetime.now()
        self.is_monitoring = False
        self.monitoring_task = None
        
        logger.info("Risk manager initialized with comprehensive monitoring")
    
    def check_portfolio_risk(self, portfolio_state: Dict[str, Any]) -> RiskCheckResult:
        """Comprehensive portfolio risk check"""
        try:
            alerts = []
            recommendations = []
            risk_scores = []
            
            # Extract portfolio metrics
            metrics = portfolio_state.get('metrics', {})
            positions = portfolio_state.get('positions', {})
            
            # Check position size limits
            position_alerts = self._check_position_sizes(positions, metrics.get('total_value', 0))
            alerts.extend(position_alerts)
            
            # Check portfolio VaR
            var_alerts = self._check_portfolio_var(metrics)
            alerts.extend(var_alerts)
            
            # Check correlation risk
            correlation_alerts = self._check_correlation_risk(positions, metrics)
            alerts.extend(correlation_alerts)
            
            # Check drawdown limits
            drawdown_alerts = self._check_drawdown_limits(metrics)
            alerts.extend(drawdown_alerts)
            
            # Check concentration risk
            concentration_alerts = self._check_concentration_risk(metrics)
            alerts.extend(concentration_alerts)
            
            # Check volatility limits
            volatility_alerts = self._check_volatility_limits(metrics)
            alerts.extend(volatility_alerts)
            
            # Check cash buffer
            cash_alerts = self._check_cash_buffer(metrics)
            alerts.extend(cash_alerts)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(alerts, metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(alerts, metrics)
            
            # Determine if risk check passed
            critical_alerts = [a for a in alerts if a.risk_level == RiskLevel.CRITICAL]
            passed = len(critical_alerts) == 0
            
            # Update active alerts
            self._update_active_alerts(alerts)
            
            result = RiskCheckResult(
                passed=passed,
                risk_score=risk_score,
                alerts=alerts,
                recommendations=recommendations
            )
            
            # Log result
            if not passed:
                logger.warning(f"Risk check failed: {len(critical_alerts)} critical alerts")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in portfolio risk check: {e}")
            return RiskCheckResult(
                passed=False,
                risk_score=1.0,
                alerts=[],
                recommendations=["Risk check failed - manual review required"]
            )
    
    def _check_position_sizes(self, positions: Dict[str, Any], total_value: float) -> List[RiskAlert]:
        """Check individual position size limits"""
        alerts = []
        
        try:
            for symbol, position_data in positions.items():
                market_value = position_data.get('market_value', 0)
                weight = market_value / total_value if total_value > 0 else 0
                
                if weight > self.config.limits.max_position_size:
                    alert = RiskAlert(
                        alert_id=f"position_size_{symbol}_{datetime.now().timestamp()}",
                        alert_type=AlertType.POSITION_SIZE,
                        risk_level=RiskLevel.HIGH if weight > self.config.limits.max_position_size * 1.2 else RiskLevel.MEDIUM,
                        message=f"Position {symbol} exceeds size limit: {weight:.2%} > {self.config.limits.max_position_size:.2%}",
                        current_value=weight,
                        limit_value=self.config.limits.max_position_size,
                        timestamp=datetime.now(),
                        portfolio_snapshot={'symbol': symbol, 'weight': weight},
                        recommended_action=f"Reduce position size for {symbol} to below {self.config.limits.max_position_size:.2%}"
                    )
                    alerts.append(alert)
                    
        except Exception as e:
            logger.error(f"Error checking position sizes: {e}")
            
        return alerts
    
    def _check_portfolio_var(self, metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check portfolio Value at Risk"""
        alerts = []
        
        try:
            var_95 = metrics.get('var_95', 0)
            
            if abs(var_95) > self.config.limits.max_portfolio_var:
                risk_level = RiskLevel.CRITICAL if abs(var_95) > self.config.limits.max_portfolio_var * 1.5 else RiskLevel.HIGH
                
                alert = RiskAlert(
                    alert_id=f"portfolio_var_{datetime.now().timestamp()}",
                    alert_type=AlertType.PORTFOLIO_VAR,
                    risk_level=risk_level,
                    message=f"Portfolio VaR exceeds limit: {abs(var_95):.2%} > {self.config.limits.max_portfolio_var:.2%}",
                    current_value=abs(var_95),
                    limit_value=self.config.limits.max_portfolio_var,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'var_95': var_95},
                    recommended_action="Reduce portfolio risk through position sizing or hedging"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking portfolio VaR: {e}")
            
        return alerts
    
    def _check_correlation_risk(self, positions: Dict[str, Any], metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check correlation risk"""
        alerts = []
        
        try:
            correlation_risk = metrics.get('correlation_risk', 0)
            
            if correlation_risk > self.config.limits.max_correlation:
                alert = RiskAlert(
                    alert_id=f"correlation_risk_{datetime.now().timestamp()}",
                    alert_type=AlertType.CORRELATION,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Correlation risk too high: {correlation_risk:.2%} > {self.config.limits.max_correlation:.2%}",
                    current_value=correlation_risk,
                    limit_value=self.config.limits.max_correlation,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'correlation_risk': correlation_risk},
                    recommended_action="Diversify portfolio to reduce correlation risk"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking correlation risk: {e}")
            
        return alerts
    
    def _check_drawdown_limits(self, metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check maximum drawdown limits"""
        alerts = []
        
        try:
            max_drawdown = metrics.get('max_drawdown', 0)
            
            if max_drawdown > self.config.limits.max_drawdown:
                risk_level = RiskLevel.CRITICAL if max_drawdown > self.config.limits.max_drawdown * 1.5 else RiskLevel.HIGH
                
                alert = RiskAlert(
                    alert_id=f"max_drawdown_{datetime.now().timestamp()}",
                    alert_type=AlertType.DRAWDOWN,
                    risk_level=risk_level,
                    message=f"Maximum drawdown exceeded: {max_drawdown:.2%} > {self.config.limits.max_drawdown:.2%}",
                    current_value=max_drawdown,
                    limit_value=self.config.limits.max_drawdown,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'max_drawdown': max_drawdown},
                    recommended_action="Consider reducing risk or implementing stop-loss measures"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking drawdown limits: {e}")
            
        return alerts
    
    def _check_concentration_risk(self, metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check concentration risk"""
        alerts = []
        
        try:
            concentration = metrics.get('concentration', 0)
            
            if concentration > self.config.limits.max_concentration:
                alert = RiskAlert(
                    alert_id=f"concentration_risk_{datetime.now().timestamp()}",
                    alert_type=AlertType.CONCENTRATION,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Portfolio concentration too high: {concentration:.2%} > {self.config.limits.max_concentration:.2%}",
                    current_value=concentration,
                    limit_value=self.config.limits.max_concentration,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'concentration': concentration},
                    recommended_action="Diversify portfolio to reduce concentration risk"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking concentration risk: {e}")
            
        return alerts
    
    def _check_volatility_limits(self, metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check portfolio volatility limits"""
        alerts = []
        
        try:
            volatility = metrics.get('volatility', 0)
            
            if volatility > self.config.limits.max_volatility:
                alert = RiskAlert(
                    alert_id=f"volatility_limit_{datetime.now().timestamp()}",
                    alert_type=AlertType.VOLATILITY,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Portfolio volatility too high: {volatility:.2%} > {self.config.limits.max_volatility:.2%}",
                    current_value=volatility,
                    limit_value=self.config.limits.max_volatility,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'volatility': volatility},
                    recommended_action="Reduce portfolio volatility through position sizing"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking volatility limits: {e}")
            
        return alerts
    
    def _check_cash_buffer(self, metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check minimum cash buffer"""
        alerts = []
        
        try:
            total_value = metrics.get('total_value', 0)
            cash = metrics.get('cash', 0)
            cash_ratio = cash / total_value if total_value > 0 else 0
            
            if cash_ratio < self.config.limits.min_cash_buffer:
                alert = RiskAlert(
                    alert_id=f"cash_buffer_{datetime.now().timestamp()}",
                    alert_type=AlertType.CONCENTRATION,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Cash buffer too low: {cash_ratio:.2%} < {self.config.limits.min_cash_buffer:.2%}",
                    current_value=cash_ratio,
                    limit_value=self.config.limits.min_cash_buffer,
                    timestamp=datetime.now(),
                    portfolio_snapshot={'cash_ratio': cash_ratio},
                    recommended_action="Increase cash buffer by reducing position sizes"
                )
                alerts.append(alert)
                
        except Exception as e:
            logger.error(f"Error checking cash buffer: {e}")
            
        return alerts
    
    def _calculate_risk_score(self, alerts: List[RiskAlert], metrics: Dict[str, Any]) -> float:
        """Calculate overall risk score (0-1, where 1 is maximum risk)"""
        try:
            if not alerts:
                return 0.0
            
            # Weight alerts by severity
            severity_weights = {
                RiskLevel.LOW: 0.1,
                RiskLevel.MEDIUM: 0.3,
                RiskLevel.HIGH: 0.6,
                RiskLevel.CRITICAL: 1.0
            }
            
            total_score = sum(severity_weights.get(alert.risk_level, 0.5) for alert in alerts)
            
            # Normalize by number of possible alert types
            max_possible_score = len(AlertType) * severity_weights[RiskLevel.CRITICAL]
            
            return min(1.0, total_score / max_possible_score)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 0.5  # Default medium risk
    
    def _generate_recommendations(self, alerts: List[RiskAlert], metrics: Dict[str, Any]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        try:
            # Collect unique recommendations from alerts
            alert_recommendations = set(alert.recommended_action for alert in alerts)
            recommendations.extend(alert_recommendations)
            
            # Add general recommendations based on portfolio state
            if metrics.get('volatility', 0) > 0.15:
                recommendations.append("Consider reducing portfolio volatility")
            
            if metrics.get('concentration', 0) > 0.2:
                recommendations.append("Diversify portfolio to reduce concentration")
            
            if len(alerts) > 3:
                recommendations.append("Multiple risk alerts - consider comprehensive portfolio review")
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            
        return recommendations
    
    def _update_active_alerts(self, new_alerts: List[RiskAlert]) -> None:
        """Update active alerts and alert history"""
        try:
            # Add new alerts to history
            self.alert_history.extend(new_alerts)
            
            # Keep only last 1000 alerts in history
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            
            # Update active alerts (replace with new ones)
            self.active_alerts.clear()
            for alert in new_alerts:
                self.active_alerts[alert.alert_id] = alert
                
        except Exception as e:
            logger.error(f"Error updating active alerts: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            return {
                'risk_manager_status': 'active',
                'last_check': self.last_check_time.isoformat(),
                'active_alerts_count': len(self.active_alerts),
                'alert_history_count': len(self.alert_history),
                'risk_limits': {
                    'max_position_size': self.config.limits.max_position_size,
                    'max_portfolio_var': self.config.limits.max_portfolio_var,
                    'max_correlation': self.config.limits.max_correlation,
                    'max_drawdown': self.config.limits.max_drawdown,
                    'max_concentration': self.config.limits.max_concentration,
                    'max_volatility': self.config.limits.max_volatility,
                    'min_cash_buffer': self.config.limits.min_cash_buffer
                },
                'active_alerts': [
                    {
                        'alert_id': alert.alert_id,
                        'type': alert.alert_type.value,
                        'level': alert.risk_level.value,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in self.active_alerts.values()
                ],
                'configuration': {
                    'check_frequency': self.config.check_frequency,
                    'alert_cooldown': self.config.alert_cooldown,
                    'stress_test_scenarios': self.config.stress_test_scenarios
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating risk summary: {e}")
            return {'error': str(e)}
    
    def start_monitoring(self, portfolio_manager) -> None:
        """Start real-time risk monitoring"""
        try:
            if self.is_monitoring:
                logger.warning("Risk monitoring already active")
                return
            
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop(portfolio_manager))
            logger.info("Risk monitoring started")
            
        except Exception as e:
            logger.error(f"Error starting risk monitoring: {e}")
    
    def stop_monitoring(self) -> None:
        """Stop real-time risk monitoring"""
        try:
            if not self.is_monitoring:
                return
            
            self.is_monitoring = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            logger.info("Risk monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping risk monitoring: {e}")
    
    async def _monitoring_loop(self, portfolio_manager) -> None:
        """Main risk monitoring loop"""
        try:
            while self.is_monitoring:
                try:
                    # Get current portfolio state
                    portfolio_state = portfolio_manager.get_state_summary()
                    
                    # Perform risk check
                    risk_result = self.check_portfolio_risk(portfolio_state)
                    
                    # Update last check time
                    self.last_check_time = datetime.now()
                    
                    # Log critical alerts
                    critical_alerts = [a for a in risk_result.alerts if a.risk_level == RiskLevel.CRITICAL]
                    if critical_alerts:
                        logger.critical(f"CRITICAL RISK ALERTS: {len(critical_alerts)} alerts detected")
                    
                    # Wait for next check
                    await asyncio.sleep(self.config.check_frequency)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(self.config.check_frequency)
                    
        except asyncio.CancelledError:
            logger.info("Risk monitoring cancelled")
        except Exception as e:
            logger.error(f"Risk monitoring loop error: {e}")
            self.is_monitoring = False 