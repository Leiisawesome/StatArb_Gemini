#!/usr/bin/env python3
"""
Comprehensive Risk Management System
Professional-grade risk management for statistical arbitrage
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Callable
import logging
from dataclasses import dataclass, field
from enum import Enum
import warnings
from collections import defaultdict, deque
import json
warnings.filterwarnings('ignore')

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    POSITION_LIMIT = "position_limit"
    PORTFOLIO_LIMIT = "portfolio_limit"
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    DRAWDOWN_LIMIT = "drawdown_limit"
    VOLATILITY_SPIKE = "volatility_spike"
    LIQUIDITY_CRISIS = "liquidity_crisis"
    CONCENTRATION_RISK = "concentration_risk"
    MARGIN_CALL = "margin_call"

@dataclass
class RiskAlert:
    """Risk alert with detailed information"""
    alert_type: AlertType
    severity: RiskLevel
    message: str
    timestamp: datetime
    affected_positions: List[str]
    current_value: float
    threshold_value: float
    recommended_action: str
    auto_executable: bool = False

@dataclass
class PositionRisk:
    """Individual position risk metrics"""
    symbol_pair: str
    current_value: float
    unrealized_pnl: float
    var_1d: float  # 1-day Value at Risk
    expected_shortfall: float  # Expected Shortfall (CVaR)
    beta_to_market: float
    correlation_breakdown_score: float
    liquidity_score: float
    concentration_risk: float
    time_decay_risk: float

@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics"""
    total_value: float
    total_pnl: float
    portfolio_var: float
    portfolio_expected_shortfall: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    correlation_matrix: np.ndarray
    sector_exposure: Dict[str, float]
    leverage_ratio: float
    liquidity_coverage_ratio: float

@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size: float = 0.1  # 10% of portfolio
    max_portfolio_var: float = 0.02  # 2% daily VaR
    max_drawdown: float = 0.05  # 5% max drawdown
    max_correlation_exposure: float = 0.3  # 30% correlated exposure
    max_leverage: float = 2.0  # 2x leverage
    max_concentration: float = 0.25  # 25% in any sector
    min_liquidity_score: float = 0.5  # Minimum liquidity requirement
    correlation_breakdown_threshold: float = 0.5  # 50% correlation drop
    volatility_spike_threshold: float = 2.0  # 2x normal volatility

class RealTimeRiskMonitor:
    """
    Real-time risk monitoring system
    
    Features:
    - Continuous P&L monitoring
    - Dynamic risk limit enforcement
    - Correlation breakdown detection
    - Stress testing and scenario analysis
    - Automated risk alerts and actions
    """
    
    def __init__(self, 
                 risk_limits: Optional[RiskLimits] = None,
                 alert_callback: Optional[Callable] = None):
        
        self.risk_limits = risk_limits or RiskLimits()
        self.alert_callback = alert_callback
        self.logger = logging.getLogger(__name__)
        
        # Risk monitoring state
        self.positions = {}
        self.historical_pnl = deque(maxlen=252)  # 1 year of daily P&L
        self.correlation_history = deque(maxlen=60)  # 60 days of correlations
        self.volatility_history = deque(maxlen=30)  # 30 days of volatility
        self.active_alerts = []
        
        # Risk metrics cache
        self.current_portfolio_risk = None
        self.last_risk_update = None
        
        # Stress test scenarios
        self.stress_scenarios = self._initialize_stress_scenarios()
        
    def _initialize_stress_scenarios(self) -> Dict[str, Dict]:
        """Initialize stress test scenarios"""
        return {
            "market_crash": {
                "description": "Market crash scenario (-20% equity, +50% volatility)",
                "equity_shock": -0.20,
                "volatility_multiplier": 1.5,
                "correlation_increase": 0.3
            },
            "liquidity_crisis": {
                "description": "Liquidity crisis (spreads widen 3x, volume drops 50%)",
                "spread_multiplier": 3.0,
                "volume_multiplier": 0.5,
                "correlation_increase": 0.4
            },
            "correlation_breakdown": {
                "description": "Correlation breakdown (pairs decorrelate by 70%)",
                "correlation_shock": -0.7,
                "volatility_multiplier": 1.2,
                "mean_reversion_speed": 0.5
            },
            "interest_rate_shock": {
                "description": "Interest rate shock (+200bps rates)",
                "rate_shock": 0.02,
                "bond_shock": -0.10,
                "volatility_multiplier": 1.3
            },
            "flash_crash": {
                "description": "Flash crash (instant -10% with recovery)",
                "instant_shock": -0.10,
                "recovery_time": 30,  # minutes
                "volatility_spike": 5.0
            }
        }
    
    def add_position(self, 
                    symbol_pair: str,
                    position_size: float,
                    entry_price: float,
                    entry_time: datetime,
                    expected_return: float,
                    volatility: float,
                    correlation: float = 0.0,
                    metadata: Optional[Dict] = None):
        """Add a new position to risk monitoring"""
        
        position = {
            'symbol_pair': symbol_pair,
            'position_size': position_size,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'expected_return': expected_return,
            'volatility': volatility,
            'correlation': correlation,
            'metadata': metadata or {},
            'historical_prices': deque(maxlen=100),
            'pnl_history': deque(maxlen=100)
        }
        
        self.positions[symbol_pair] = position
        self.logger.info(f"Added position to risk monitoring: {symbol_pair}")
        
        # Check immediate risk limits
        self._check_position_limits(symbol_pair)
    
    def update_position(self, 
                       symbol_pair: str,
                       current_price: float,
                       timestamp: datetime,
                       volume: Optional[float] = None,
                       spread: Optional[float] = None):
        """Update position with current market data"""
        
        if symbol_pair not in self.positions:
            self.logger.warning(f"Position {symbol_pair} not found in risk monitoring")
            return
        
        position = self.positions[symbol_pair]
        
        # Update price history
        position['historical_prices'].append({
            'price': current_price,
            'timestamp': timestamp,
            'volume': volume,
            'spread': spread
        })
        
        # Calculate current P&L
        entry_price = position['entry_price']
        current_pnl = position['position_size'] * (current_price - entry_price) / entry_price
        position['pnl_history'].append({
            'pnl': current_pnl,
            'timestamp': timestamp
        })
        
        # Update risk metrics
        self._update_position_risk_metrics(symbol_pair)
        
        # Check risk limits
        self._check_all_risk_limits()
    
    def _update_position_risk_metrics(self, symbol_pair: str):
        """Update risk metrics for a specific position"""
        
        position = self.positions[symbol_pair]
        
        if len(position['pnl_history']) < 2:
            return
        
        # Calculate VaR and Expected Shortfall
        pnl_series = [p['pnl'] for p in position['pnl_history']]
        var_1d = np.percentile(pnl_series, 5)  # 5% VaR
        expected_shortfall = np.mean([p for p in pnl_series if p <= var_1d])
        
        # Calculate correlation breakdown score
        correlation_breakdown_score = self._calculate_correlation_breakdown(symbol_pair)
        
        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(symbol_pair)
        
        # Update position risk
        position['risk_metrics'] = {
            'var_1d': var_1d,
            'expected_shortfall': expected_shortfall,
            'correlation_breakdown_score': correlation_breakdown_score,
            'liquidity_score': liquidity_score,
            'current_pnl': pnl_series[-1] if pnl_series else 0.0
        }
    
    def _calculate_correlation_breakdown(self, symbol_pair: str) -> float:
        """Calculate correlation breakdown risk score"""
        
        position = self.positions[symbol_pair]
        
        if len(position['pnl_history']) < 20:
            return 0.0
        
        # Get recent P&L
        recent_pnl = [p['pnl'] for p in list(position['pnl_history'])[-20:]]
        
        # Calculate rolling correlation with expected pattern
        expected_correlation = position['correlation']
        
        # Mock calculation - in practice, would use actual pair correlation
        recent_correlation = np.corrcoef(recent_pnl, range(len(recent_pnl)))[0, 1]
        
        # Breakdown score (higher = more breakdown)
        breakdown_score = abs(expected_correlation - recent_correlation)
        
        return min(1.0, breakdown_score)
    
    def _calculate_liquidity_score(self, symbol_pair: str) -> float:
        """Calculate liquidity score for position"""
        
        position = self.positions[symbol_pair]
        
        if len(position['historical_prices']) < 5:
            return 0.5  # Default neutral score
        
        # Get recent market data
        recent_data = list(position['historical_prices'])[-5:]
        
        # Volume-based liquidity
        volumes = [d.get('volume', 0) for d in recent_data if d.get('volume')]
        avg_volume = np.mean(volumes) if volumes else 0
        volume_score = min(1.0, avg_volume / 100000)  # Normalize to 100k baseline
        
        # Spread-based liquidity
        spreads = [d.get('spread', 0.001) for d in recent_data if d.get('spread')]
        avg_spread = np.mean(spreads) if spreads else 0.001
        spread_score = max(0.0, 1.0 - avg_spread * 1000)  # Penalize wide spreads
        
        # Combined liquidity score
        liquidity_score = (volume_score * 0.6 + spread_score * 0.4)
        
        return max(0.0, min(1.0, liquidity_score))
    
    def _check_position_limits(self, symbol_pair: str):
        """Check position-specific risk limits"""
        
        position = self.positions[symbol_pair]
        alerts = []
        
        # Position size limit
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        position_weight = position['position_size'] / portfolio_value
        
        if position_weight > self.risk_limits.max_position_size:
            alerts.append(RiskAlert(
                alert_type=AlertType.POSITION_LIMIT,
                severity=RiskLevel.HIGH,
                message=f"Position {symbol_pair} exceeds size limit",
                timestamp=datetime.now(),
                affected_positions=[symbol_pair],
                current_value=position_weight,
                threshold_value=self.risk_limits.max_position_size,
                recommended_action="Reduce position size",
                auto_executable=True
            ))
        
        # Correlation breakdown
        if 'risk_metrics' in position:
            breakdown_score = position['risk_metrics'].get('correlation_breakdown_score', 0)
            if breakdown_score > self.risk_limits.correlation_breakdown_threshold:
                alerts.append(RiskAlert(
                    alert_type=AlertType.CORRELATION_BREAKDOWN,
                    severity=RiskLevel.MEDIUM,
                    message=f"Correlation breakdown detected in {symbol_pair}",
                    timestamp=datetime.now(),
                    affected_positions=[symbol_pair],
                    current_value=breakdown_score,
                    threshold_value=self.risk_limits.correlation_breakdown_threshold,
                    recommended_action="Review pair relationship, consider exit",
                    auto_executable=False
                ))
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _check_all_risk_limits(self):
        """Check all portfolio-level risk limits"""
        
        if not self.positions:
            return
        
        alerts = []
        
        # Calculate portfolio metrics
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        total_pnl = sum(p['risk_metrics'].get('current_pnl', 0) 
                       for p in self.positions.values() 
                       if 'risk_metrics' in p)
        
        # Portfolio VaR
        portfolio_var = self._calculate_portfolio_var()
        if portfolio_var > self.risk_limits.max_portfolio_var * portfolio_value:
            alerts.append(RiskAlert(
                alert_type=AlertType.PORTFOLIO_LIMIT,
                severity=RiskLevel.HIGH,
                message="Portfolio VaR exceeds limit",
                timestamp=datetime.now(),
                affected_positions=list(self.positions.keys()),
                current_value=portfolio_var / portfolio_value,
                threshold_value=self.risk_limits.max_portfolio_var,
                recommended_action="Reduce overall portfolio risk",
                auto_executable=True
            ))
        
        # Drawdown limit
        current_drawdown = self._calculate_current_drawdown()
        if current_drawdown > self.risk_limits.max_drawdown:
            alerts.append(RiskAlert(
                alert_type=AlertType.DRAWDOWN_LIMIT,
                severity=RiskLevel.CRITICAL,
                message=f"Drawdown limit exceeded: {current_drawdown:.2%}",
                timestamp=datetime.now(),
                affected_positions=list(self.positions.keys()),
                current_value=current_drawdown,
                threshold_value=self.risk_limits.max_drawdown,
                recommended_action="Emergency position reduction",
                auto_executable=True
            ))
        
        # Concentration risk
        concentration_risk = self._calculate_concentration_risk()
        if concentration_risk > self.risk_limits.max_concentration:
            alerts.append(RiskAlert(
                alert_type=AlertType.CONCENTRATION_RISK,
                severity=RiskLevel.MEDIUM,
                message="Portfolio concentration exceeds limit",
                timestamp=datetime.now(),
                affected_positions=list(self.positions.keys()),
                current_value=concentration_risk,
                threshold_value=self.risk_limits.max_concentration,
                recommended_action="Diversify portfolio",
                auto_executable=False
            ))
        
        # Process alerts
        for alert in alerts:
            self._process_alert(alert)
    
    def _calculate_portfolio_var(self) -> float:
        """Calculate portfolio Value at Risk"""
        
        if len(self.positions) < 2:
            return 0.0
        
        # Simplified VaR calculation
        position_vars = []
        position_weights = []
        
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        
        for position in self.positions.values():
            if 'risk_metrics' in position:
                var = position['risk_metrics'].get('var_1d', 0)
                weight = position['position_size'] / portfolio_value
                position_vars.append(var)
                position_weights.append(weight)
        
        if not position_vars:
            return 0.0
        
        # Portfolio VaR with correlation (simplified)
        weighted_var = sum(w * v for w, v in zip(position_weights, position_vars))
        
        # Apply diversification benefit (assume 70% correlation)
        diversification_factor = 0.7
        portfolio_var = weighted_var * np.sqrt(diversification_factor)
        
        return portfolio_var * portfolio_value
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current portfolio drawdown"""
        
        if len(self.historical_pnl) < 2:
            return 0.0
        
        # Calculate cumulative P&L
        cumulative_pnl = np.cumsum(list(self.historical_pnl))
        
        # Calculate running maximum
        running_max = np.maximum.accumulate(cumulative_pnl)
        
        # Current drawdown
        current_drawdown = (cumulative_pnl[-1] - running_max[-1]) / abs(running_max[-1])
        
        return abs(current_drawdown)
    
    def _calculate_concentration_risk(self) -> float:
        """Calculate portfolio concentration risk"""
        
        if not self.positions:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        weights = [p['position_size'] / portfolio_value for p in self.positions.values()]
        
        hhi = sum(w**2 for w in weights)
        
        # Convert to concentration score (0-1, higher = more concentrated)
        if len(weights) <= 1:
            concentration_score = 1.0  # Single position = maximum concentration
        else:
            concentration_score = (hhi - 1/len(weights)) / (1 - 1/len(weights))
        
        return max(0.0, min(1.0, float(concentration_score)))
    
    def _process_alert(self, alert: RiskAlert):
        """Process a risk alert"""
        
        # Add to active alerts
        self.active_alerts.append(alert)
        
        # Log alert
        self.logger.warning(f"RISK ALERT [{alert.severity.value.upper()}]: {alert.message}")
        
        # Call alert callback if provided
        if self.alert_callback:
            self.alert_callback(alert)
        
        # Auto-execute if enabled
        if alert.auto_executable:
            self._execute_risk_action(alert)
    
    def _execute_risk_action(self, alert: RiskAlert):
        """Execute automatic risk management action"""
        
        self.logger.info(f"Executing risk action: {alert.recommended_action}")
        
        if alert.alert_type == AlertType.POSITION_LIMIT:
            # Reduce position size
            for symbol_pair in alert.affected_positions:
                if symbol_pair in self.positions:
                    reduction_factor = alert.threshold_value / alert.current_value
                    self.positions[symbol_pair]['position_size'] *= reduction_factor
                    self.logger.info(f"Reduced {symbol_pair} position by {(1-reduction_factor)*100:.1f}%")
        
        elif alert.alert_type == AlertType.DRAWDOWN_LIMIT:
            # Emergency position reduction
            reduction_factor = 0.5  # Reduce all positions by 50%
            for position in self.positions.values():
                position['position_size'] *= reduction_factor
            self.logger.info("Emergency position reduction: 50% across all positions")
        
        elif alert.alert_type == AlertType.PORTFOLIO_LIMIT:
            # Reduce overall portfolio risk
            reduction_factor = alert.threshold_value / alert.current_value
            for position in self.positions.values():
                position['position_size'] *= reduction_factor
            self.logger.info(f"Portfolio risk reduction: {(1-reduction_factor)*100:.1f}%")
    
    def run_stress_test(self, scenario_name: str) -> Dict:
        """Run stress test on current portfolio"""
        
        if scenario_name not in self.stress_scenarios:
            raise ValueError(f"Unknown stress scenario: {scenario_name}")
        
        scenario = self.stress_scenarios[scenario_name]
        results = {
            'scenario': scenario_name,
            'description': scenario['description'],
            'timestamp': datetime.now(),
            'position_impacts': {},
            'portfolio_impact': {}
        }
        
        total_stress_pnl = 0.0
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        
        for symbol_pair, position in self.positions.items():
            # Apply scenario shocks
            stress_pnl = self._calculate_stress_pnl(position, scenario)
            
            results['position_impacts'][symbol_pair] = {
                'stress_pnl': stress_pnl,
                'stress_return': stress_pnl / position['position_size'],
                'position_size': position['position_size']
            }
            
            total_stress_pnl += stress_pnl
        
        # Portfolio-level impact
        results['portfolio_impact'] = {
            'total_stress_pnl': total_stress_pnl,
            'stress_return': total_stress_pnl / portfolio_value,
            'stressed_var': self._calculate_stressed_var(scenario),
            'survival_probability': self._calculate_survival_probability(total_stress_pnl, portfolio_value)
        }
        
        return results
    
    def _calculate_stress_pnl(self, position: Dict, scenario: Dict) -> float:
        """Calculate P&L under stress scenario"""
        
        base_pnl = position['risk_metrics'].get('current_pnl', 0.0) if 'risk_metrics' in position else 0.0
        
        # Apply scenario-specific shocks
        if 'equity_shock' in scenario:
            equity_impact = position['position_size'] * scenario['equity_shock']
            base_pnl += equity_impact
        
        if 'volatility_multiplier' in scenario:
            vol_impact = position['position_size'] * position['volatility'] * (scenario['volatility_multiplier'] - 1) * 0.1
            base_pnl -= vol_impact  # Higher volatility = negative impact
        
        if 'correlation_shock' in scenario:
            corr_impact = position['position_size'] * abs(scenario['correlation_shock']) * 0.05
            base_pnl -= corr_impact  # Correlation breakdown = negative impact
        
        return base_pnl
    
    def _calculate_stressed_var(self, scenario: Dict) -> float:
        """Calculate VaR under stress scenario"""
        
        base_var = self._calculate_portfolio_var()
        
        # Apply stress multipliers
        stress_multiplier = 1.0
        
        if 'volatility_multiplier' in scenario:
            stress_multiplier *= scenario['volatility_multiplier']
        
        if 'correlation_increase' in scenario:
            stress_multiplier *= (1 + scenario['correlation_increase'])
        
        return base_var * stress_multiplier
    
    def _calculate_survival_probability(self, stress_pnl: float, portfolio_value: float) -> float:
        """Calculate probability of surviving stress scenario"""
        
        stress_return = stress_pnl / portfolio_value
        
        # Simple survival probability based on stress severity
        if stress_return > -0.05:  # Less than 5% loss
            return 0.95
        elif stress_return > -0.10:  # 5-10% loss
            return 0.80
        elif stress_return > -0.20:  # 10-20% loss
            return 0.60
        elif stress_return > -0.30:  # 20-30% loss
            return 0.30
        else:  # More than 30% loss
            return 0.10
    
    def generate_risk_report(self) -> str:
        """Generate comprehensive risk management report"""
        
        if not self.positions:
            return "No positions to analyze."
        
        # Calculate portfolio metrics
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        total_pnl = sum(p['risk_metrics'].get('current_pnl', 0) 
                       for p in self.positions.values() 
                       if 'risk_metrics' in p)
        
        portfolio_var = self._calculate_portfolio_var()
        current_drawdown = self._calculate_current_drawdown()
        concentration_risk = self._calculate_concentration_risk()
        
        # Active alerts summary
        alert_summary = defaultdict(int)
        for alert in self.active_alerts:
            alert_summary[alert.severity] += 1
        
        report = f"""
=== COMPREHENSIVE RISK MANAGEMENT REPORT ===
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Portfolio Value: ${portfolio_value:,.0f}
Total P&L: ${total_pnl:,.0f} ({total_pnl/portfolio_value:.2%})

=== RISK METRICS ===
Portfolio VaR (1-day): ${portfolio_var:,.0f} ({portfolio_var/portfolio_value:.2%})
Current Drawdown: {current_drawdown:.2%}
Concentration Risk: {concentration_risk:.2%}
Number of Positions: {len(self.positions)}

=== RISK LIMITS STATUS ===
Position Size Limit: {self.risk_limits.max_position_size:.1%}
Portfolio VaR Limit: {self.risk_limits.max_portfolio_var:.1%}
Drawdown Limit: {self.risk_limits.max_drawdown:.1%}
Concentration Limit: {self.risk_limits.max_concentration:.1%}

=== ACTIVE ALERTS ===
"""
        
        if alert_summary:
            for severity, count in alert_summary.items():
                report += f"{severity.value.upper()}: {count} alerts\n"
        else:
            report += "No active alerts\n"
        
        report += "\n=== POSITION RISK ANALYSIS ===\n"
        
        for symbol_pair, position in self.positions.items():
            if 'risk_metrics' in position:
                metrics = position['risk_metrics']
                report += f"""
{symbol_pair}:
  Position Size: ${position['position_size']:,.0f}
  Current P&L: ${metrics.get('current_pnl', 0):,.0f}
  VaR (1-day): ${metrics.get('var_1d', 0):,.0f}
  Correlation Breakdown: {metrics.get('correlation_breakdown_score', 0):.2f}
  Liquidity Score: {metrics.get('liquidity_score', 0):.2f}
"""
        
        # Stress test summary
        report += "\n=== STRESS TEST SUMMARY ===\n"
        
        for scenario_name in ['market_crash', 'liquidity_crisis', 'correlation_breakdown']:
            try:
                stress_result = self.run_stress_test(scenario_name)
                impact = stress_result['portfolio_impact']
                report += f"""
{scenario_name.replace('_', ' ').title()}:
  Stress P&L: ${impact['total_stress_pnl']:,.0f} ({impact['stress_return']:.2%})
  Survival Probability: {impact['survival_probability']:.1%}
"""
            except Exception as e:
                report += f"{scenario_name}: Error - {str(e)}\n"
        
        report += """
=== RISK MANAGEMENT CAPABILITIES ===
✓ Real-time P&L monitoring
✓ Dynamic risk limit enforcement
✓ Correlation breakdown detection
✓ Automated risk alerts
✓ Stress testing and scenario analysis
✓ Position-level risk controls
✓ Portfolio-level risk management
✓ Liquidity risk monitoring
✓ Concentration risk analysis
"""
        
        return report
    
    def get_risk_dashboard_data(self) -> Dict:
        """Get risk data for dashboard/UI"""
        
        portfolio_value = sum(p['position_size'] for p in self.positions.values())
        total_pnl = sum(p['risk_metrics'].get('current_pnl', 0) 
                       for p in self.positions.values() 
                       if 'risk_metrics' in p)
        
        return {
            'portfolio_value': portfolio_value,
            'total_pnl': total_pnl,
            'portfolio_var': self._calculate_portfolio_var(),
            'current_drawdown': self._calculate_current_drawdown(),
            'concentration_risk': self._calculate_concentration_risk(),
            'active_alerts': len(self.active_alerts),
            'positions_count': len(self.positions),
            'risk_limits': {
                'max_position_size': self.risk_limits.max_position_size,
                'max_portfolio_var': self.risk_limits.max_portfolio_var,
                'max_drawdown': self.risk_limits.max_drawdown,
                'max_concentration': self.risk_limits.max_concentration
            },
            'timestamp': datetime.now()
        }

# Integration with existing systems
class RiskManagedTradingSystem:
    """Trading system with integrated risk management"""
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Initialize risk monitor
        self.risk_monitor = RealTimeRiskMonitor(
            alert_callback=self._handle_risk_alert
        )
        
        self.positions = {}
        self.trade_history = []
        
    def _handle_risk_alert(self, alert: RiskAlert):
        """Handle risk alerts from monitoring system"""
        
        print(f"🚨 RISK ALERT: {alert.message}")
        print(f"   Severity: {alert.severity.value.upper()}")
        print(f"   Action: {alert.recommended_action}")
        
        # Log to trade history
        self.trade_history.append({
            'type': 'risk_alert',
            'timestamp': alert.timestamp,
            'alert_type': alert.alert_type.value,
            'message': alert.message,
            'auto_executed': alert.auto_executable
        })
    
    def execute_trade(self, 
                     symbol_pair: str,
                     position_size: float,
                     expected_return: float,
                     volatility: float,
                     correlation: float = 0.0) -> bool:
        """Execute trade with risk management"""
        
        # Pre-trade risk check
        if not self._pre_trade_risk_check(symbol_pair, position_size):
            return False
        
        # Execute trade
        entry_price = 100.0  # Mock price
        entry_time = datetime.now()
        
        # Add to risk monitoring
        self.risk_monitor.add_position(
            symbol_pair=symbol_pair,
            position_size=position_size,
            entry_price=entry_price,
            entry_time=entry_time,
            expected_return=expected_return,
            volatility=volatility,
            correlation=correlation
        )
        
        # Update capital
        self.current_capital -= position_size
        
        # Record trade
        self.trade_history.append({
            'type': 'trade_execution',
            'symbol_pair': symbol_pair,
            'position_size': position_size,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'timestamp': datetime.now()
        })
        
        return True
    
    def _pre_trade_risk_check(self, symbol_pair: str, position_size: float) -> bool:
        """Pre-trade risk validation"""
        
        # Check position size limit
        portfolio_value = self.current_capital + sum(p['position_size'] for p in self.risk_monitor.positions.values())
        position_weight = position_size / portfolio_value
        
        if position_weight > self.risk_monitor.risk_limits.max_position_size:
            print(f"❌ Trade rejected: Position size exceeds limit ({position_weight:.1%} > {self.risk_monitor.risk_limits.max_position_size:.1%})")
            return False
        
        # Check available capital
        if position_size > self.current_capital:
            print(f"❌ Trade rejected: Insufficient capital (${position_size:,.0f} > ${self.current_capital:,.0f})")
            return False
        
        return True
    
    def update_market_data(self, symbol_pair: str, price: float, volume: float = None, spread: float = None):
        """Update market data for risk monitoring"""
        
        self.risk_monitor.update_position(
            symbol_pair=symbol_pair,
            current_price=price,
            timestamp=datetime.now(),
            volume=volume,
            spread=spread
        )
    
    def run_risk_demo(self, duration_minutes: int = 3) -> None:
        """Run risk management demo"""
        
        print("🛡️  Starting Risk-Managed Trading System Demo")
        print(f"💰 Initial Capital: ${self.initial_capital:,.0f}")
        print(f"⏱️  Demo Duration: {duration_minutes} minutes")
        print("=" * 60)
        
        # Sample trades
        trades = [
            {'pair': 'TSLA_NVDA', 'size': 50000, 'return': 0.02, 'vol': 0.25, 'corr': 0.3},
            {'pair': 'QQQ_TQQQ', 'size': 80000, 'return': 0.015, 'vol': 0.18, 'corr': 0.1},
            {'pair': 'TLT_TMF', 'size': 60000, 'return': 0.01, 'vol': 0.12, 'corr': -0.2},
            {'pair': 'GOOGL_META', 'size': 70000, 'return': 0.018, 'vol': 0.22, 'corr': 0.4},
            {'pair': 'BABA_YINN', 'size': 90000, 'return': 0.025, 'vol': 0.30, 'corr': 0.2}
        ]
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        cycle = 0
        
        while datetime.now() < end_time:
            cycle += 1
            
            print(f"\n📊 Risk Management Cycle {cycle}")
            print(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
            
            # Execute trades (one per cycle)
            if cycle <= len(trades):
                trade = trades[cycle - 1]
                success = self.execute_trade(
                    symbol_pair=trade['pair'],
                    position_size=trade['size'],
                    expected_return=trade['return'],
                    volatility=trade['vol'],
                    correlation=trade['corr']
                )
                
                if success:
                    print(f"✅ Executed: {trade['pair']} - ${trade['size']:,.0f}")
                else:
                    print(f"❌ Rejected: {trade['pair']} - Risk limits exceeded")
            
            # Update market data (simulate price movements)
            for symbol_pair in self.risk_monitor.positions.keys():
                # Simulate price movement
                price_change = np.random.normal(0, 0.02)
                new_price = 100 * (1 + price_change)
                
                self.update_market_data(
                    symbol_pair=symbol_pair,
                    price=new_price,
                    volume=float(np.random.lognormal(10, 1)),
                    spread=float(np.random.uniform(0.0005, 0.002))
                )
            
            # Display risk metrics
            dashboard_data = self.risk_monitor.get_risk_dashboard_data()
            print(f"💼 Portfolio Value: ${dashboard_data['portfolio_value']:,.0f}")
            print(f"📈 Total P&L: ${dashboard_data['total_pnl']:,.0f}")
            print(f"⚠️  Active Alerts: {dashboard_data['active_alerts']}")
            print(f"🎯 Positions: {dashboard_data['positions_count']}")
            
            # Run stress test occasionally
            if cycle % 3 == 0 and self.risk_monitor.positions:
                print("\n🧪 Running Stress Test: Market Crash")
                stress_result = self.risk_monitor.run_stress_test('market_crash')
                impact = stress_result['portfolio_impact']
                print(f"   Stress P&L: ${impact['total_stress_pnl']:,.0f} ({impact['stress_return']:.2%})")
                print(f"   Survival Probability: {impact['survival_probability']:.1%}")
            
            # Wait before next cycle
            import time
            time.sleep(20)  # 20 second cycles
        
        # Final risk report
        print("\n" + "=" * 60)
        print("📋 FINAL RISK MANAGEMENT REPORT")
        print("=" * 60)
        print(self.risk_monitor.generate_risk_report())

# Example usage
if __name__ == "__main__":
    # Initialize risk-managed trading system
    system = RiskManagedTradingSystem(initial_capital=1000000)
    
    # Run demo
    system.run_risk_demo(duration_minutes=2) 