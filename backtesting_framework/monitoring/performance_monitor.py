#!/usr/bin/env python3
"""
Performance Monitoring System
Phase 2: Core System Integration - Batch 5
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Performance metrics calculation"""
    
    def __init__(self):
        self.metrics_history = []
        self.current_metrics = {}
        
        logger.info("Initialized PerformanceMetrics")
    
    def calculate_metrics(self, portfolio_value: float, initial_capital: float,
                         returns: List[float], benchmark_returns: List[float] = None) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        # Basic metrics
        total_return = (portfolio_value - initial_capital) / initial_capital
        
        # Calculate returns if not provided
        if not returns:
            returns = [0.0]  # Default to avoid division by zero
        
        # Risk metrics
        volatility = np.std(returns) if len(returns) > 1 else 0.0
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        excess_returns = [r - risk_free_rate/252 for r in returns]  # Daily excess returns
        sharpe_ratio = np.mean(excess_returns) / volatility * np.sqrt(252) if volatility > 0 else 0.0
        
        # Sortino ratio
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = np.std(negative_returns) if negative_returns else 0.0
        sortino_ratio = np.mean(excess_returns) / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0.0
        
        # Maximum drawdown
        cumulative_returns = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0.0
        
        # Information ratio (if benchmark provided)
        information_ratio = 0.0
        if benchmark_returns and len(benchmark_returns) == len(returns):
            active_returns = [r - br for r, br in zip(returns, benchmark_returns)]
            tracking_error = np.std(active_returns) if len(active_returns) > 1 else 0.0
            information_ratio = np.mean(active_returns) / tracking_error * np.sqrt(252) if tracking_error > 0 else 0.0
        
        # Win rate
        winning_trades = sum(1 for r in returns if r > 0)
        total_trades = len(returns)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Average win/loss
        avg_win = np.mean([r for r in returns if r > 0]) if any(r > 0 for r in returns) else 0.0
        avg_loss = np.mean([r for r in returns if r < 0]) if any(r < 0 for r in returns) else 0.0
        
        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        metrics = {
            'timestamp': datetime.now(),
            'portfolio_value': portfolio_value,
            'initial_capital': initial_capital,
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'information_ratio': information_ratio,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'winning_trades': winning_trades
        }
        
        self.current_metrics = metrics
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 records
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        logger.debug(f"Calculated performance metrics: {total_return:.2%} return, {sharpe_ratio:.3f} Sharpe")
        return metrics
    
    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary"""
        if not self.current_metrics:
            return {}
        
        return {
            'total_return': self.current_metrics['total_return'],
            'sharpe_ratio': self.current_metrics['sharpe_ratio'],
            'sortino_ratio': self.current_metrics['sortino_ratio'],
            'max_drawdown': self.current_metrics['max_drawdown'],
            'win_rate': self.current_metrics['win_rate'],
            'profit_factor': self.current_metrics['profit_factor'],
            'total_trades': self.current_metrics['total_trades']
        }
    
    def get_metrics_history(self, lookback_periods: int = 100) -> pd.DataFrame:
        """Get metrics history as DataFrame"""
        if not self.metrics_history:
            return pd.DataFrame()
        
        history = self.metrics_history[-lookback_periods:]
        df = pd.DataFrame(history)
        df.set_index('timestamp', inplace=True)
        return df

class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.performance_metrics = PerformanceMetrics()
        self.monitoring_callbacks = []
        self.alert_callbacks = []
        
        # Performance tracking
        self.portfolio_values = []
        self.returns = []
        self.benchmark_returns = []
        self.performance_alerts = []
        
        # Alert thresholds
        self.alert_thresholds = {
            'drawdown_alert': 0.10,  # 10% drawdown alert
            'sharpe_alert': 0.5,     # Sharpe ratio below 0.5 alert
            'loss_alert': -0.05,     # 5% daily loss alert
            'volatility_alert': 0.25  # 25% volatility alert
        }
        
        logger.info(f"Initialized PerformanceMonitor with ${initial_capital:,.2f} initial capital")
    
    def add_monitoring_callback(self, callback: Callable):
        """Add callback for performance monitoring events"""
        self.monitoring_callbacks.append(callback)
        logger.info(f"Added monitoring callback: {callback.__name__}")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def update_performance(self, portfolio_value: float, daily_return: float = None,
                          benchmark_return: float = None):
        """Update performance metrics"""
        
        # Store portfolio value
        self.portfolio_values.append(portfolio_value)
        
        # Calculate daily return if not provided
        if daily_return is None and len(self.portfolio_values) > 1:
            daily_return = (portfolio_value - self.portfolio_values[-2]) / self.portfolio_values[-2]
        elif daily_return is None:
            daily_return = 0.0
        
        # Store returns
        self.returns.append(daily_return)
        if benchmark_return is not None:
            self.benchmark_returns.append(benchmark_return)
        
        # Calculate metrics
        metrics = self.performance_metrics.calculate_metrics(
            portfolio_value, self.initial_capital, self.returns, self.benchmark_returns
        )
        
        # Check for alerts
        alerts = self._check_alerts(metrics)
        if alerts:
            self.performance_alerts.extend(alerts)
            for alert in alerts:
                for callback in self.alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")
        
        # Notify monitoring callbacks
        for callback in self.monitoring_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Monitoring callback error: {e}")
        
        logger.debug(f"Updated performance: {portfolio_value:,.2f}, {daily_return:.2%} return")
    
    def _check_alerts(self, metrics: Dict) -> List[Dict]:
        """Check for performance alerts"""
        alerts = []
        
        # Drawdown alert
        if metrics['max_drawdown'] <= -self.alert_thresholds['drawdown_alert']:
            alerts.append({
                'type': 'DRAWDOWN_ALERT',
                'message': f"Maximum drawdown exceeded: {metrics['max_drawdown']:.2%}",
                'severity': 'HIGH',
                'timestamp': datetime.now()
            })
        
        # Sharpe ratio alert
        if metrics['sharpe_ratio'] < self.alert_thresholds['sharpe_alert']:
            alerts.append({
                'type': 'SHARPE_ALERT',
                'message': f"Sharpe ratio below threshold: {metrics['sharpe_ratio']:.3f}",
                'severity': 'MEDIUM',
                'timestamp': datetime.now()
            })
        
        # Daily loss alert
        if len(self.returns) > 0 and self.returns[-1] < self.alert_thresholds['loss_alert']:
            alerts.append({
                'type': 'LOSS_ALERT',
                'message': f"Daily loss exceeded: {self.returns[-1]:.2%}",
                'severity': 'HIGH',
                'timestamp': datetime.now()
            })
        
        # Volatility alert
        if metrics['volatility'] > self.alert_thresholds['volatility_alert']:
            alerts.append({
                'type': 'VOLATILITY_ALERT',
                'message': f"Volatility above threshold: {metrics['volatility']:.2%}",
                'severity': 'MEDIUM',
                'timestamp': datetime.now()
            })
        
        return alerts
    
    def get_performance_summary(self) -> Dict:
        """Get performance monitoring summary"""
        metrics_summary = self.performance_metrics.get_metrics_summary()
        
        return {
            'initial_capital': self.initial_capital,
            'current_portfolio_value': self.portfolio_values[-1] if self.portfolio_values else self.initial_capital,
            'total_return': metrics_summary.get('total_return', 0.0),
            'sharpe_ratio': metrics_summary.get('sharpe_ratio', 0.0),
            'sortino_ratio': metrics_summary.get('sortino_ratio', 0.0),
            'max_drawdown': metrics_summary.get('max_drawdown', 0.0),
            'win_rate': metrics_summary.get('win_rate', 0.0),
            'profit_factor': metrics_summary.get('profit_factor', 0.0),
            'total_trades': metrics_summary.get('total_trades', 0),
            'performance_alerts_count': len(self.performance_alerts),
            'monitoring_callbacks_count': len(self.monitoring_callbacks),
            'alert_callbacks_count': len(self.alert_callbacks)
        }
    
    def get_performance_history(self, lookback_periods: int = 100) -> pd.DataFrame:
        """Get performance history"""
        return self.performance_metrics.get_metrics_history(lookback_periods) 