"""
Performance Degradation Alert System
====================================

This module provides comprehensive performance degradation monitoring and alerting
for statistical arbitrage pairs, with intelligent notification systems and
automated risk management recommendations.

Key Features:
- Multi-dimensional performance monitoring
- Intelligent alert prioritization
- Automated risk management recommendations
- Performance attribution analysis
- Predictive degradation detection
- Notification system with multiple channels

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import sqlite3
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from collections import defaultdict, deque
import threading
import time
import warnings

# Statistical libraries
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_squared_error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertPriority(Enum):
    """Alert priority levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class PerformanceMetric(Enum):
    """Performance metrics to monitor"""
    SHARPE_RATIO = "SHARPE_RATIO"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    WIN_RATE = "WIN_RATE"
    PROFIT_FACTOR = "PROFIT_FACTOR"
    CALMAR_RATIO = "CALMAR_RATIO"
    SORTINO_RATIO = "SORTINO_RATIO"
    VAR_95 = "VAR_95"
    EXPECTED_SHORTFALL = "EXPECTED_SHORTFALL"
    CORRELATION_STABILITY = "CORRELATION_STABILITY"
    STRATEGY_CAPACITY = "STRATEGY_CAPACITY"

class DegradationType(Enum):
    """Types of performance degradation"""
    GRADUAL_DECLINE = "GRADUAL_DECLINE"
    SUDDEN_DROP = "SUDDEN_DROP"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    CORRELATION_BREAKDOWN = "CORRELATION_BREAKDOWN"
    CAPACITY_CONSTRAINT = "CAPACITY_CONSTRAINT"
    REGIME_CHANGE = "REGIME_CHANGE"
    MARKET_STRESS = "MARKET_STRESS"
    EXECUTION_ISSUES = "EXECUTION_ISSUES"

class NotificationChannel(Enum):
    """Notification channels"""
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"
    SMS = "SMS"
    DASHBOARD = "DASHBOARD"

@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics"""
    pair_id: str
    timestamp: datetime
    
    # Core performance metrics
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    
    # Risk metrics
    var_95: float
    expected_shortfall: float
    correlation_stability: float
    
    # Trading metrics
    total_trades: int
    avg_trade_duration: float
    avg_profit_per_trade: float
    
    # Market context
    market_regime: str
    volatility_regime: str
    correlation_level: float
    
    # Derived metrics
    performance_score: float
    risk_score: float
    stability_score: float

@dataclass
class PerformanceAlert:
    """Performance degradation alert"""
    alert_id: str
    pair_id: str
    timestamp: datetime
    priority: AlertPriority
    
    # Alert details
    alert_type: str
    degradation_type: DegradationType
    metric_affected: PerformanceMetric
    
    # Performance impact
    current_value: float
    historical_average: float
    degradation_percentage: float
    statistical_significance: float
    
    # Context
    trigger_conditions: List[str]
    contributing_factors: List[str]
    market_context: Dict[str, Any]
    
    # Recommendations
    immediate_actions: List[str]
    risk_adjustments: List[str]
    investigation_steps: List[str]
    
    # Notification
    notification_channels: List[NotificationChannel]
    escalation_required: bool
    
    # Status
    acknowledged: bool = False
    resolved: bool = False
    resolution_notes: str = ""

@dataclass
class PerformanceThresholds:
    """Performance degradation thresholds"""
    sharpe_ratio_min: float = 0.5
    max_drawdown_max: float = 0.15
    win_rate_min: float = 0.45
    profit_factor_min: float = 1.1
    correlation_stability_min: float = 0.6
    
    # Alert thresholds (percentage degradation)
    minor_degradation: float = 0.1  # 10%
    moderate_degradation: float = 0.2  # 20%
    severe_degradation: float = 0.3  # 30%
    critical_degradation: float = 0.5  # 50%

class PerformanceAlertSystem:
    """
    Comprehensive performance degradation alert system
    
    This class provides:
    - Real-time performance monitoring
    - Intelligent alert generation
    - Multi-channel notifications
    - Risk management recommendations
    - Performance attribution analysis
    """
    
    def __init__(self, 
                 db_path: str = "performance_alerts.db",
                 monitoring_window: int = 252,  # Trading days
                 alert_frequency: int = 300,  # 5 minutes
                 notification_config: Dict[str, Any] = None):
        """
        Initialize the performance alert system
        
        Args:
            db_path: Path to SQLite database
            monitoring_window: Window for performance calculation
            alert_frequency: Alert check frequency in seconds
            notification_config: Configuration for notifications
        """
        self.db_path = db_path
        self.monitoring_window = monitoring_window
        self.alert_frequency = alert_frequency
        self.notification_config = notification_config or {}
        
        # Performance data storage
        self.performance_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.monitoring_window * 2)
        )
        self.trade_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Alert management
        self.active_alerts: List[PerformanceAlert] = []
        self.alert_history: List[PerformanceAlert] = []
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Thresholds and configuration
        self.thresholds = PerformanceThresholds()
        self.monitoring_enabled = True
        
        # Anomaly detection
        self.anomaly_detectors: Dict[str, IsolationForest] = {}
        
        # Threading
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize database
        self._init_database()
        
        logger.info("Performance alert system initialized")
    
    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    calmar_ratio REAL,
                    sortino_ratio REAL,
                    var_95 REAL,
                    expected_shortfall REAL,
                    correlation_stability REAL,
                    total_trades INTEGER,
                    avg_trade_duration REAL,
                    avg_profit_per_trade REAL,
                    market_regime TEXT,
                    volatility_regime TEXT,
                    correlation_level REAL,
                    performance_score REAL,
                    risk_score REAL,
                    stability_score REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    priority TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    degradation_type TEXT NOT NULL,
                    metric_affected TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    historical_average REAL NOT NULL,
                    degradation_percentage REAL NOT NULL,
                    statistical_significance REAL NOT NULL,
                    trigger_conditions TEXT,
                    contributing_factors TEXT,
                    market_context TEXT,
                    immediate_actions TEXT,
                    risk_adjustments TEXT,
                    investigation_steps TEXT,
                    notification_channels TEXT,
                    escalation_required BOOLEAN,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    trade_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    pnl REAL NOT NULL,
                    duration INTEGER NOT NULL,
                    fees REAL DEFAULT 0,
                    slippage REAL DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Performance alert database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_trade_record(self, pair_id: str, trade_type: str, entry_price: float,
                        exit_price: float, quantity: float, pnl: float,
                        duration: int, fees: float = 0.0, slippage: float = 0.0,
                        timestamp: datetime = None):
        """Add a trade record for performance calculation"""
        if timestamp is None:
            timestamp = datetime.now()
        
        trade_record = {
            'timestamp': timestamp,
            'trade_type': trade_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'duration': duration,
            'fees': fees,
            'slippage': slippage
        }
        
        self.trade_history[pair_id].append(trade_record)
        
        # Store in database
        self._store_trade_record(pair_id, trade_record)
        
        # Update performance metrics
        self._update_performance_metrics(pair_id)
    
    def _store_trade_record(self, pair_id: str, trade_record: Dict[str, Any]):
        """Store trade record in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trade_records 
                (pair_id, timestamp, trade_type, entry_price, exit_price, quantity,
                 pnl, duration, fees, slippage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pair_id, trade_record['timestamp'], trade_record['trade_type'],
                trade_record['entry_price'], trade_record['exit_price'],
                trade_record['quantity'], trade_record['pnl'],
                trade_record['duration'], trade_record['fees'],
                trade_record['slippage']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing trade record: {e}")
    
    def _update_performance_metrics(self, pair_id: str):
        """Update performance metrics for a pair"""
        try:
            trades = list(self.trade_history[pair_id])
            if len(trades) < 10:  # Need minimum trades for meaningful metrics
                return
            
            # Calculate performance metrics
            snapshot = self._calculate_performance_snapshot(pair_id, trades)
            
            # Store snapshot
            self.performance_history[pair_id].append(snapshot)
            self._store_performance_snapshot(snapshot)
            
            # Check for performance degradation
            self._check_performance_degradation(pair_id, snapshot)
            
        except Exception as e:
            logger.error(f"Error updating performance metrics for {pair_id}: {e}")
    
    def _calculate_performance_snapshot(self, pair_id: str, trades: List[Dict[str, Any]]) -> PerformanceSnapshot:
        """Calculate comprehensive performance snapshot"""
        try:
            # Extract trade data
            pnls = np.array([trade['pnl'] for trade in trades])
            durations = np.array([trade['duration'] for trade in trades])
            
            # Basic statistics
            total_return = np.sum(pnls)
            win_rate = np.mean(pnls > 0)
            avg_profit_per_trade = np.mean(pnls)
            
            # Risk-adjusted metrics
            if np.std(pnls) > 0:
                sharpe_ratio = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
            
            # Downside risk metrics
            negative_returns = pnls[pnls < 0]
            if len(negative_returns) > 0:
                downside_std = np.std(negative_returns)
                sortino_ratio = np.mean(pnls) / downside_std * np.sqrt(252) if downside_std > 0 else 0.0
            else:
                sortino_ratio = sharpe_ratio
            
            # Drawdown calculation
            cumulative_pnl = np.cumsum(pnls)
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = (cumulative_pnl - running_max) / (running_max + 1e-8)
            max_drawdown = np.min(drawdown)
            
            # Profit factor
            gross_profit = np.sum(pnls[pnls > 0])
            gross_loss = abs(np.sum(pnls[pnls < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            
            # Calmar ratio
            calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
            
            # VaR and Expected Shortfall
            var_95 = np.percentile(pnls, 5)
            tail_losses = pnls[pnls <= var_95]
            expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_95
            
            # Correlation stability (placeholder - would need price data)
            correlation_stability = 0.8  # Would calculate from actual correlation data
            
            # Derived scores
            performance_score = self._calculate_performance_score(sharpe_ratio, max_drawdown, win_rate)
            risk_score = self._calculate_risk_score(max_drawdown, var_95, expected_shortfall)
            stability_score = self._calculate_stability_score(pnls, correlation_stability)
            
            return PerformanceSnapshot(
                pair_id=pair_id,
                timestamp=datetime.now(),
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                correlation_stability=correlation_stability,
                total_trades=len(trades),
                avg_trade_duration=np.mean(durations),
                avg_profit_per_trade=avg_profit_per_trade,
                market_regime="NORMAL",  # Would integrate with regime detection
                volatility_regime="MODERATE",
                correlation_level=0.7,  # Would calculate from actual data
                performance_score=performance_score,
                risk_score=risk_score,
                stability_score=stability_score
            )
            
        except Exception as e:
            logger.error(f"Error calculating performance snapshot: {e}")
            return self._create_default_snapshot(pair_id)
    
    def _create_default_snapshot(self, pair_id: str) -> PerformanceSnapshot:
        """Create default performance snapshot"""
        return PerformanceSnapshot(
            pair_id=pair_id,
            timestamp=datetime.now(),
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.5,
            profit_factor=1.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0,
            var_95=0.0,
            expected_shortfall=0.0,
            correlation_stability=0.5,
            total_trades=0,
            avg_trade_duration=0.0,
            avg_profit_per_trade=0.0,
            market_regime="UNKNOWN",
            volatility_regime="UNKNOWN",
            correlation_level=0.0,
            performance_score=0.0,
            risk_score=0.0,
            stability_score=0.0
        )
    
    def _calculate_performance_score(self, sharpe_ratio: float, max_drawdown: float, win_rate: float) -> float:
        """Calculate overall performance score"""
        # Normalize metrics to 0-1 scale
        sharpe_score = min(1.0, max(0.0, sharpe_ratio / 2.0))  # Normalize by 2.0
        drawdown_score = min(1.0, max(0.0, 1.0 - abs(max_drawdown) / 0.3))  # Normalize by 30%
        win_rate_score = min(1.0, max(0.0, (win_rate - 0.3) / 0.4))  # Normalize from 30-70%
        
        # Weighted combination
        performance_score = (
            0.4 * sharpe_score +
            0.3 * drawdown_score +
            0.3 * win_rate_score
        )
        
        return performance_score
    
    def _calculate_risk_score(self, max_drawdown: float, var_95: float, expected_shortfall: float) -> float:
        """Calculate risk score"""
        # Higher risk = higher score
        drawdown_risk = min(1.0, abs(max_drawdown) / 0.3)
        var_risk = min(1.0, abs(var_95) / 0.05)  # Normalize by 5%
        es_risk = min(1.0, abs(expected_shortfall) / 0.08)  # Normalize by 8%
        
        risk_score = (
            0.4 * drawdown_risk +
            0.3 * var_risk +
            0.3 * es_risk
        )
        
        return risk_score
    
    def _calculate_stability_score(self, pnls: np.ndarray, correlation_stability: float) -> float:
        """Calculate stability score"""
        # PnL stability
        pnl_stability = 1.0 / (1.0 + np.std(pnls) / (abs(np.mean(pnls)) + 1e-8))
        
        # Combined stability
        stability_score = (
            0.6 * pnl_stability +
            0.4 * correlation_stability
        )
        
        return min(1.0, max(0.0, stability_score))
    
    def _store_performance_snapshot(self, snapshot: PerformanceSnapshot):
        """Store performance snapshot in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_snapshots 
                (pair_id, timestamp, sharpe_ratio, max_drawdown, win_rate, profit_factor,
                 calmar_ratio, sortino_ratio, var_95, expected_shortfall, correlation_stability,
                 total_trades, avg_trade_duration, avg_profit_per_trade, market_regime,
                 volatility_regime, correlation_level, performance_score, risk_score, stability_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot.pair_id, snapshot.timestamp, snapshot.sharpe_ratio,
                snapshot.max_drawdown, snapshot.win_rate, snapshot.profit_factor,
                snapshot.calmar_ratio, snapshot.sortino_ratio, snapshot.var_95,
                snapshot.expected_shortfall, snapshot.correlation_stability,
                snapshot.total_trades, snapshot.avg_trade_duration,
                snapshot.avg_profit_per_trade, snapshot.market_regime,
                snapshot.volatility_regime, snapshot.correlation_level,
                snapshot.performance_score, snapshot.risk_score, snapshot.stability_score
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance snapshot: {e}")
    
    def _check_performance_degradation(self, pair_id: str, current_snapshot: PerformanceSnapshot):
        """Check for performance degradation and generate alerts"""
        try:
            history = list(self.performance_history[pair_id])
            if len(history) < 10:  # Need history for comparison
                return
            
            # Calculate historical averages
            historical_snapshots = history[:-1]  # Exclude current
            historical_metrics = self._calculate_historical_averages(historical_snapshots)
            
            # Check each metric for degradation
            degradation_alerts = []
            
            # Sharpe ratio degradation
            if self._check_metric_degradation(
                current_snapshot.sharpe_ratio,
                historical_metrics['sharpe_ratio'],
                PerformanceMetric.SHARPE_RATIO,
                higher_is_better=True
            ):
                degradation_alerts.append(PerformanceMetric.SHARPE_RATIO)
            
            # Max drawdown degradation
            if self._check_metric_degradation(
                current_snapshot.max_drawdown,
                historical_metrics['max_drawdown'],
                PerformanceMetric.MAX_DRAWDOWN,
                higher_is_better=False
            ):
                degradation_alerts.append(PerformanceMetric.MAX_DRAWDOWN)
            
            # Win rate degradation
            if self._check_metric_degradation(
                current_snapshot.win_rate,
                historical_metrics['win_rate'],
                PerformanceMetric.WIN_RATE,
                higher_is_better=True
            ):
                degradation_alerts.append(PerformanceMetric.WIN_RATE)
            
            # Profit factor degradation
            if self._check_metric_degradation(
                current_snapshot.profit_factor,
                historical_metrics['profit_factor'],
                PerformanceMetric.PROFIT_FACTOR,
                higher_is_better=True
            ):
                degradation_alerts.append(PerformanceMetric.PROFIT_FACTOR)
            
            # Generate alerts for degraded metrics
            for metric in degradation_alerts:
                self._generate_performance_alert(pair_id, current_snapshot, historical_metrics, metric)
            
            # Check for anomalies using ML
            self._check_anomalies(pair_id, current_snapshot, historical_snapshots)
            
        except Exception as e:
            logger.error(f"Error checking performance degradation for {pair_id}: {e}")
    
    def _calculate_historical_averages(self, snapshots: List[PerformanceSnapshot]) -> Dict[str, float]:
        """Calculate historical averages for comparison"""
        if not snapshots:
            return {}
        
        return {
            'sharpe_ratio': np.mean([s.sharpe_ratio for s in snapshots]),
            'max_drawdown': np.mean([s.max_drawdown for s in snapshots]),
            'win_rate': np.mean([s.win_rate for s in snapshots]),
            'profit_factor': np.mean([s.profit_factor for s in snapshots]),
            'calmar_ratio': np.mean([s.calmar_ratio for s in snapshots]),
            'sortino_ratio': np.mean([s.sortino_ratio for s in snapshots]),
            'var_95': np.mean([s.var_95 for s in snapshots]),
            'expected_shortfall': np.mean([s.expected_shortfall for s in snapshots]),
            'correlation_stability': np.mean([s.correlation_stability for s in snapshots])
        }
    
    def _check_metric_degradation(self, current_value: float, historical_average: float,
                                metric: PerformanceMetric, higher_is_better: bool) -> bool:
        """Check if a metric has degraded significantly"""
        if historical_average == 0:
            return False
        
        # Calculate percentage change
        if higher_is_better:
            degradation_pct = (historical_average - current_value) / abs(historical_average)
        else:
            degradation_pct = (current_value - historical_average) / abs(historical_average)
        
        # Check against thresholds
        return degradation_pct > self.thresholds.moderate_degradation
    
    def _generate_performance_alert(self, pair_id: str, current_snapshot: PerformanceSnapshot,
                                  historical_metrics: Dict[str, float], metric: PerformanceMetric):
        """Generate performance degradation alert"""
        try:
            # Get current and historical values
            current_value = getattr(current_snapshot, metric.value.lower())
            historical_average = historical_metrics.get(metric.value.lower(), 0.0)
            
            # Calculate degradation
            if historical_average != 0:
                degradation_pct = abs(current_value - historical_average) / abs(historical_average)
            else:
                degradation_pct = 0.0
            
            # Determine priority and degradation type
            priority = self._determine_alert_priority(degradation_pct, metric)
            degradation_type = self._determine_degradation_type(current_snapshot, historical_metrics)
            
            # Statistical significance
            significance = self._calculate_statistical_significance(pair_id, metric, current_value)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(metric, degradation_pct, current_snapshot)
            
            # Create alert
            alert = PerformanceAlert(
                alert_id=f"{pair_id}_{metric.value}_{int(datetime.now().timestamp())}",
                pair_id=pair_id,
                timestamp=datetime.now(),
                priority=priority,
                alert_type="PERFORMANCE_DEGRADATION",
                degradation_type=degradation_type,
                metric_affected=metric,
                current_value=current_value,
                historical_average=historical_average,
                degradation_percentage=degradation_pct,
                statistical_significance=significance,
                trigger_conditions=self._identify_trigger_conditions(current_snapshot, historical_metrics),
                contributing_factors=self._identify_contributing_factors(current_snapshot),
                market_context=self._get_market_context(current_snapshot),
                immediate_actions=recommendations['immediate_actions'],
                risk_adjustments=recommendations['risk_adjustments'],
                investigation_steps=recommendations['investigation_steps'],
                notification_channels=self._determine_notification_channels(priority),
                escalation_required=priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY]
            )
            
            # Store and process alert
            self.active_alerts.append(alert)
            self.alert_history.append(alert)
            self._store_performance_alert(alert)
            
            # Send notifications
            self._send_notifications(alert)
            
            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            logger.warning(f"Performance alert generated for {pair_id}: {metric.value} degradation {degradation_pct:.1%}")
            
        except Exception as e:
            logger.error(f"Error generating performance alert: {e}")
    
    def _determine_alert_priority(self, degradation_pct: float, metric: PerformanceMetric) -> AlertPriority:
        """Determine alert priority based on degradation severity"""
        if degradation_pct > 0.8:  # 80% degradation
            return AlertPriority.EMERGENCY
        elif degradation_pct > 0.5:  # 50% degradation
            return AlertPriority.CRITICAL
        elif degradation_pct > 0.3:  # 30% degradation
            return AlertPriority.HIGH
        elif degradation_pct > 0.15:  # 15% degradation
            return AlertPriority.MEDIUM
        else:
            return AlertPriority.LOW
    
    def _determine_degradation_type(self, current_snapshot: PerformanceSnapshot,
                                  historical_metrics: Dict[str, float]) -> DegradationType:
        """Determine the type of degradation"""
        # Check for sudden drops
        if current_snapshot.performance_score < 0.3 and historical_metrics.get('performance_score', 0.5) > 0.7:
            return DegradationType.SUDDEN_DROP
        
        # Check for correlation issues
        if current_snapshot.correlation_stability < 0.4:
            return DegradationType.CORRELATION_BREAKDOWN
        
        # Check for volatility spikes
        if current_snapshot.risk_score > 0.8:
            return DegradationType.VOLATILITY_SPIKE
        
        # Check for capacity constraints
        if current_snapshot.total_trades > 100 and current_snapshot.avg_profit_per_trade < 0:
            return DegradationType.CAPACITY_CONSTRAINT
        
        # Default to gradual decline
        return DegradationType.GRADUAL_DECLINE
    
    def _calculate_statistical_significance(self, pair_id: str, metric: PerformanceMetric, 
                                          current_value: float) -> float:
        """Calculate statistical significance of degradation"""
        try:
            history = list(self.performance_history[pair_id])
            if len(history) < 10:
                return 0.0
            
            # Get historical values for the metric
            historical_values = [getattr(s, metric.value.lower()) for s in history[:-1]]
            
            # Perform t-test
            t_stat, p_value = stats.ttest_1samp(historical_values, current_value)
            
            # Return significance level (1 - p_value)
            return 1.0 - p_value
            
        except Exception as e:
            logger.error(f"Error calculating statistical significance: {e}")
            return 0.0
    
    def _identify_trigger_conditions(self, current_snapshot: PerformanceSnapshot,
                                   historical_metrics: Dict[str, float]) -> List[str]:
        """Identify conditions that triggered the alert"""
        conditions = []
        
        # Sharpe ratio conditions
        if current_snapshot.sharpe_ratio < self.thresholds.sharpe_ratio_min:
            conditions.append("SHARPE_RATIO_BELOW_THRESHOLD")
        
        # Drawdown conditions
        if abs(current_snapshot.max_drawdown) > self.thresholds.max_drawdown_max:
            conditions.append("MAX_DRAWDOWN_EXCEEDED")
        
        # Win rate conditions
        if current_snapshot.win_rate < self.thresholds.win_rate_min:
            conditions.append("WIN_RATE_BELOW_THRESHOLD")
        
        # Correlation conditions
        if current_snapshot.correlation_stability < self.thresholds.correlation_stability_min:
            conditions.append("CORRELATION_INSTABILITY")
        
        return conditions if conditions else ["GENERAL_DEGRADATION"]
    
    def _identify_contributing_factors(self, current_snapshot: PerformanceSnapshot) -> List[str]:
        """Identify factors contributing to degradation"""
        factors = []
        
        # Market regime factors
        if current_snapshot.market_regime == "CRISIS":
            factors.append("MARKET_CRISIS")
        elif current_snapshot.volatility_regime == "HIGH":
            factors.append("HIGH_VOLATILITY_REGIME")
        
        # Trading factors
        if current_snapshot.avg_trade_duration > 1440:  # > 1 day
            factors.append("LONG_TRADE_DURATION")
        
        if current_snapshot.total_trades > 50:  # High frequency
            factors.append("HIGH_FREQUENCY_TRADING")
        
        # Risk factors
        if current_snapshot.risk_score > 0.7:
            factors.append("HIGH_RISK_ENVIRONMENT")
        
        return factors if factors else ["UNKNOWN_FACTORS"]
    
    def _get_market_context(self, snapshot: PerformanceSnapshot) -> Dict[str, Any]:
        """Get market context for the alert"""
        return {
            'market_regime': snapshot.market_regime,
            'volatility_regime': snapshot.volatility_regime,
            'correlation_level': snapshot.correlation_level,
            'risk_environment': 'HIGH' if snapshot.risk_score > 0.7 else 'NORMAL',
            'timestamp': snapshot.timestamp.isoformat()
        }
    
    def _generate_recommendations(self, metric: PerformanceMetric, degradation_pct: float,
                                snapshot: PerformanceSnapshot) -> Dict[str, List[str]]:
        """Generate recommendations based on degradation"""
        recommendations = {
            'immediate_actions': [],
            'risk_adjustments': [],
            'investigation_steps': []
        }
        
        # Immediate actions based on severity
        if degradation_pct > 0.5:  # Critical degradation
            recommendations['immediate_actions'].extend([
                "HALT_TRADING_IMMEDIATELY",
                "REVIEW_POSITIONS",
                "NOTIFY_RISK_MANAGEMENT"
            ])
        elif degradation_pct > 0.3:  # High degradation
            recommendations['immediate_actions'].extend([
                "REDUCE_POSITION_SIZE",
                "TIGHTEN_STOP_LOSSES",
                "INCREASE_MONITORING"
            ])
        else:
            recommendations['immediate_actions'].append("INCREASE_MONITORING_FREQUENCY")
        
        # Risk adjustments
        if snapshot.risk_score > 0.7:
            recommendations['risk_adjustments'].extend([
                "REDUCE_LEVERAGE",
                "IMPLEMENT_ADDITIONAL_HEDGING",
                "LOWER_POSITION_LIMITS"
            ])
        
        # Investigation steps
        recommendations['investigation_steps'].extend([
            "ANALYZE_RECENT_TRADES",
            "CHECK_CORRELATION_STABILITY",
            "REVIEW_MARKET_CONDITIONS",
            "VALIDATE_DATA_QUALITY"
        ])
        
        # Metric-specific recommendations
        if metric == PerformanceMetric.SHARPE_RATIO:
            recommendations['investigation_steps'].append("ANALYZE_RETURN_VOLATILITY_RELATIONSHIP")
        elif metric == PerformanceMetric.MAX_DRAWDOWN:
            recommendations['investigation_steps'].append("REVIEW_RISK_MANAGEMENT_RULES")
        elif metric == PerformanceMetric.WIN_RATE:
            recommendations['investigation_steps'].append("ANALYZE_ENTRY_EXIT_SIGNALS")
        
        return recommendations
    
    def _determine_notification_channels(self, priority: AlertPriority) -> List[NotificationChannel]:
        """Determine notification channels based on priority"""
        channels = [NotificationChannel.DASHBOARD]  # Always notify dashboard
        
        if priority in [AlertPriority.MEDIUM, AlertPriority.HIGH]:
            channels.append(NotificationChannel.EMAIL)
        
        if priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]:
            channels.append(NotificationChannel.SLACK)
        
        if priority == AlertPriority.CRITICAL:
            channels.append(NotificationChannel.WEBHOOK)
        
        if priority == AlertPriority.EMERGENCY:
            channels.extend([NotificationChannel.SMS, NotificationChannel.WEBHOOK])
        
        return channels
    
    def _check_anomalies(self, pair_id: str, current_snapshot: PerformanceSnapshot,
                        historical_snapshots: List[PerformanceSnapshot]):
        """Check for anomalies using machine learning"""
        try:
            if len(historical_snapshots) < 20:
                return
            
            # Prepare feature matrix
            features = []
            for snapshot in historical_snapshots:
                features.append([
                    snapshot.sharpe_ratio,
                    snapshot.max_drawdown,
                    snapshot.win_rate,
                    snapshot.profit_factor,
                    snapshot.performance_score,
                    snapshot.risk_score,
                    snapshot.stability_score
                ])
            
            features = np.array(features)
            
            # Train or update anomaly detector
            if pair_id not in self.anomaly_detectors:
                self.anomaly_detectors[pair_id] = IsolationForest(contamination=0.1, random_state=42)
                self.anomaly_detectors[pair_id].fit(features)
            
            # Check current snapshot for anomalies
            current_features = np.array([[
                current_snapshot.sharpe_ratio,
                current_snapshot.max_drawdown,
                current_snapshot.win_rate,
                current_snapshot.profit_factor,
                current_snapshot.performance_score,
                current_snapshot.risk_score,
                current_snapshot.stability_score
            ]])
            
            anomaly_score = self.anomaly_detectors[pair_id].decision_function(current_features)[0]
            is_anomaly = self.anomaly_detectors[pair_id].predict(current_features)[0] == -1
            
            if is_anomaly:
                self._generate_anomaly_alert(pair_id, current_snapshot, anomaly_score)
            
        except Exception as e:
            logger.error(f"Error checking anomalies for {pair_id}: {e}")
    
    def _generate_anomaly_alert(self, pair_id: str, snapshot: PerformanceSnapshot, anomaly_score: float):
        """Generate anomaly alert"""
        try:
            alert = PerformanceAlert(
                alert_id=f"{pair_id}_ANOMALY_{int(datetime.now().timestamp())}",
                pair_id=pair_id,
                timestamp=datetime.now(),
                priority=AlertPriority.HIGH,
                alert_type="PERFORMANCE_ANOMALY",
                degradation_type=DegradationType.SUDDEN_DROP,
                metric_affected=PerformanceMetric.SHARPE_RATIO,  # Default
                current_value=snapshot.performance_score,
                historical_average=0.5,  # Placeholder
                degradation_percentage=0.5,  # Placeholder
                statistical_significance=abs(anomaly_score),
                trigger_conditions=["ANOMALY_DETECTED"],
                contributing_factors=["STATISTICAL_ANOMALY"],
                market_context=self._get_market_context(snapshot),
                immediate_actions=["INVESTIGATE_ANOMALY", "REVIEW_DATA_QUALITY"],
                risk_adjustments=["REDUCE_EXPOSURE"],
                investigation_steps=["ANALYZE_ANOMALY_FEATURES", "CHECK_DATA_INTEGRITY"],
                notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                escalation_required=True
            )
            
            self.active_alerts.append(alert)
            self._store_performance_alert(alert)
            self._send_notifications(alert)
            
            logger.warning(f"Anomaly alert generated for {pair_id}: score {anomaly_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error generating anomaly alert: {e}")
    
    def _store_performance_alert(self, alert: PerformanceAlert):
        """Store performance alert in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_alerts 
                (alert_id, pair_id, timestamp, priority, alert_type, degradation_type,
                 metric_affected, current_value, historical_average, degradation_percentage,
                 statistical_significance, trigger_conditions, contributing_factors,
                 market_context, immediate_actions, risk_adjustments, investigation_steps,
                 notification_channels, escalation_required, acknowledged, resolved, resolution_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id, alert.pair_id, alert.timestamp, alert.priority.value,
                alert.alert_type, alert.degradation_type.value, alert.metric_affected.value,
                alert.current_value, alert.historical_average, alert.degradation_percentage,
                alert.statistical_significance, json.dumps(alert.trigger_conditions),
                json.dumps(alert.contributing_factors), json.dumps(alert.market_context),
                json.dumps(alert.immediate_actions), json.dumps(alert.risk_adjustments),
                json.dumps(alert.investigation_steps), 
                json.dumps([ch.value for ch in alert.notification_channels]),
                alert.escalation_required, alert.acknowledged, alert.resolved, alert.resolution_notes
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance alert: {e}")
    
    def _send_notifications(self, alert: PerformanceAlert):
        """Send notifications through configured channels"""
        for channel in alert.notification_channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert)
                elif channel == NotificationChannel.SLACK:
                    self._send_slack_notification(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert)
                elif channel == NotificationChannel.SMS:
                    self._send_sms_notification(alert)
                # Dashboard notifications are handled by the UI
                
            except Exception as e:
                logger.error(f"Error sending {channel.value} notification: {e}")
    
    def _send_email_notification(self, alert: PerformanceAlert):
        """Send email notification"""
        if not self.notification_config.get('email'):
            return
        
        config = self.notification_config['email']
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config['from_email']
        msg['To'] = config['to_email']
        msg['Subject'] = f"Performance Alert: {alert.pair_id} - {alert.priority.value}"
        
        # Email body
        body = f"""
        Performance Alert Generated
        
        Pair: {alert.pair_id}
        Priority: {alert.priority.value}
        Alert Type: {alert.alert_type}
        Metric Affected: {alert.metric_affected.value}
        
        Current Value: {alert.current_value:.4f}
        Historical Average: {alert.historical_average:.4f}
        Degradation: {alert.degradation_percentage:.1%}
        
        Immediate Actions:
        {chr(10).join(f"- {action}" for action in alert.immediate_actions)}
        
        Risk Adjustments:
        {chr(10).join(f"- {adjustment}" for adjustment in alert.risk_adjustments)}
        
        Timestamp: {alert.timestamp}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
            server.quit()
            logger.info(f"Email notification sent for alert {alert.alert_id}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _send_slack_notification(self, alert: PerformanceAlert):
        """Send Slack notification"""
        if not self.notification_config.get('slack'):
            return
        
        webhook_url = self.notification_config['slack']['webhook_url']
        
        # Create Slack message
        message = {
            "text": f"🚨 Performance Alert: {alert.pair_id}",
            "attachments": [{
                "color": "danger" if alert.priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY] else "warning",
                "fields": [
                    {"title": "Priority", "value": alert.priority.value, "short": True},
                    {"title": "Metric", "value": alert.metric_affected.value, "short": True},
                    {"title": "Degradation", "value": f"{alert.degradation_percentage:.1%}", "short": True},
                    {"title": "Actions", "value": "\n".join(alert.immediate_actions), "short": False}
                ],
                "timestamp": int(alert.timestamp.timestamp())
            }]
        }
        
        try:
            response = requests.post(webhook_url, json=message)
            response.raise_for_status()
            logger.info(f"Slack notification sent for alert {alert.alert_id}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _send_webhook_notification(self, alert: PerformanceAlert):
        """Send webhook notification"""
        if not self.notification_config.get('webhook'):
            return
        
        webhook_url = self.notification_config['webhook']['url']
        
        # Create webhook payload
        payload = {
            "alert_id": alert.alert_id,
            "pair_id": alert.pair_id,
            "timestamp": alert.timestamp.isoformat(),
            "priority": alert.priority.value,
            "alert_type": alert.alert_type,
            "metric_affected": alert.metric_affected.value,
            "current_value": alert.current_value,
            "degradation_percentage": alert.degradation_percentage,
            "immediate_actions": alert.immediate_actions,
            "escalation_required": alert.escalation_required
        }
        
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Webhook notification sent for alert {alert.alert_id}")
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    def _send_sms_notification(self, alert: PerformanceAlert):
        """Send SMS notification (placeholder)"""
        # This would integrate with SMS service like Twilio
        logger.info(f"SMS notification would be sent for alert {alert.alert_id}")
    
    def start_monitoring(self):
        """Start performance monitoring"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Monitoring already running")
            return
        
        self.monitoring_enabled = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_enabled = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_enabled and not self.stop_event.is_set():
            try:
                # Check for stale alerts that need escalation
                self._check_alert_escalation()
                
                # Clean up old alerts
                self._cleanup_old_alerts()
                
                # Sleep until next check
                self.stop_event.wait(self.alert_frequency)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_alert_escalation(self):
        """Check if alerts need escalation"""
        current_time = datetime.now()
        
        for alert in self.active_alerts:
            if (not alert.acknowledged and 
                alert.escalation_required and 
                (current_time - alert.timestamp).total_seconds() > 3600):  # 1 hour
                
                # Escalate alert
                self._escalate_alert(alert)
    
    def _escalate_alert(self, alert: PerformanceAlert):
        """Escalate an unacknowledged alert"""
        try:
            # Upgrade priority
            if alert.priority == AlertPriority.HIGH:
                alert.priority = AlertPriority.CRITICAL
            elif alert.priority == AlertPriority.CRITICAL:
                alert.priority = AlertPriority.EMERGENCY
            
            # Send escalation notifications
            escalation_channels = [NotificationChannel.EMAIL, NotificationChannel.SLACK]
            if alert.priority == AlertPriority.EMERGENCY:
                escalation_channels.append(NotificationChannel.SMS)
            
            # Update notification channels
            alert.notification_channels = escalation_channels
            
            # Send notifications
            self._send_notifications(alert)
            
            logger.warning(f"Alert {alert.alert_id} escalated to {alert.priority.value}")
            
        except Exception as e:
            logger.error(f"Error escalating alert: {e}")
    
    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        # Remove old resolved alerts from active list
        self.active_alerts = [
            alert for alert in self.active_alerts
            if not alert.resolved or alert.timestamp > cutoff_time
        ]
    
    def get_active_alerts(self, pair_id: str = None) -> List[PerformanceAlert]:
        """Get active alerts"""
        alerts = [alert for alert in self.active_alerts if not alert.resolved]
        
        if pair_id:
            alerts = [alert for alert in alerts if alert.pair_id == pair_id]
        
        return alerts
    
    def acknowledge_alert(self, alert_id: str, notes: str = ""):
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                if notes:
                    alert.resolution_notes = notes
                
                # Update database
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE performance_alerts 
                        SET acknowledged = TRUE, resolution_notes = ?
                        WHERE alert_id = ?
                    ''', (notes, alert_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error acknowledging alert: {e}")
                
                logger.info(f"Alert {alert_id} acknowledged")
                break
    
    def resolve_alert(self, alert_id: str, resolution_notes: str):
        """Resolve an alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolution_notes = resolution_notes
                
                # Update database
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE performance_alerts 
                        SET resolved = TRUE, resolution_notes = ?
                        WHERE alert_id = ?
                    ''', (resolution_notes, alert_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Error resolving alert: {e}")
                
                logger.info(f"Alert {alert_id} resolved: {resolution_notes}")
                break
    
    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system summary"""
        active_alerts = self.get_active_alerts()
        
        return {
            'monitoring_enabled': self.monitoring_enabled,
            'pairs_monitored': len(self.performance_history),
            'active_alerts': len(active_alerts),
            'critical_alerts': len([a for a in active_alerts if a.priority in [AlertPriority.CRITICAL, AlertPriority.EMERGENCY]]),
            'unacknowledged_alerts': len([a for a in active_alerts if not a.acknowledged]),
            'alert_breakdown': {
                priority.value: len([a for a in active_alerts if a.priority == priority])
                for priority in AlertPriority
            },
            'last_update': datetime.now().isoformat()
        }

# Example usage
if __name__ == "__main__":
    # Create alert system
    alert_system = PerformanceAlertSystem()
    
    # Add callback
    def alert_handler(alert: PerformanceAlert):
        print(f"PERFORMANCE ALERT: {alert.pair_id} - {alert.metric_affected.value} - {alert.priority.value}")
    
    alert_system.add_alert_callback(alert_handler)
    
    # Start monitoring
    alert_system.start_monitoring()
    
    # Simulate some trades
    import random
    
    for i in range(50):
        pnl = random.gauss(0.001, 0.01)  # Small positive expected return with volatility
        if i > 30:  # Simulate degradation
            pnl = random.gauss(-0.002, 0.02)  # Negative expected return with higher volatility
        
        alert_system.add_trade_record(
            pair_id="TSLA_NVDA",
            trade_type="LONG_SHORT",
            entry_price=100.0,
            exit_price=100.0 + pnl,
            quantity=1.0,
            pnl=pnl,
            duration=60  # 1 minute
        )
    
    # Get summary
    summary = alert_system.get_system_summary()
    print(json.dumps(summary, indent=2))
    
    # Stop monitoring
    alert_system.stop_monitoring() 