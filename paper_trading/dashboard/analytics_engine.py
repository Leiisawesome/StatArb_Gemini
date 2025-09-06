#!/usr/bin/env python3
"""
Real-Time Analytics Engine
==========================

Advanced analytics engine for real-time trading performance analysis.
Provides sophisticated metrics, risk analysis, and performance attribution.

Author: Pro Quant Desk Trader
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsResult:
    """Analytics calculation result"""
    metric_name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None

class RealTimeAnalytics:
    """
    Real-time analytics engine for trading performance
    
    Provides advanced analytics including:
    - Risk-adjusted returns
    - Performance attribution
    - Strategy correlation analysis
    - Real-time risk metrics
    - Trade execution analytics
    """
    
    def __init__(self, lookback_periods: int = 252):
        self.lookback_periods = lookback_periods  # Trading days for calculations
        
        # Data storage for calculations
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        self.return_history: Dict[str, List[float]] = defaultdict(list)
        self.portfolio_history: List[float] = []
        self.timestamp_history: List[datetime] = []
        
        # Strategy tracking
        self.strategy_returns: Dict[str, List[float]] = defaultdict(list)
        self.strategy_allocations: Dict[str, float] = {}
        
        # Risk-free rate (annualized)
        self.risk_free_rate = 0.02  # 2% annual
        
        logger.info("📈 Real-Time Analytics Engine initialized")
    
    def update_data(self, snapshot, performance_metrics):
        """Update analytics with new data snapshot"""
        try:
            # Update portfolio history
            self.portfolio_history.append(snapshot.portfolio_value)
            self.timestamp_history.append(snapshot.timestamp)
            
            # Limit history size
            if len(self.portfolio_history) > self.lookback_periods:
                self.portfolio_history.pop(0)
                self.timestamp_history.pop(0)
            
            # Update strategy data
            for strategy_id, perf_data in snapshot.strategy_performance.items():
                strategy_value = perf_data.get('allocated_capital', 0) + perf_data.get('current_pnl', 0)
                
                # Calculate strategy return
                if strategy_id in self.strategy_returns and len(self.strategy_returns[strategy_id]) > 0:
                    prev_value = self.strategy_returns[strategy_id][-1]
                    if prev_value > 0:
                        strategy_return = (strategy_value - prev_value) / prev_value
                        self.strategy_returns[strategy_id].append(strategy_return)
                else:
                    self.strategy_returns[strategy_id].append(0.0)
                
                # Update allocation
                self.strategy_allocations[strategy_id] = perf_data.get('allocation', 0.0)
                
                # Limit history
                if len(self.strategy_returns[strategy_id]) > self.lookback_periods:
                    self.strategy_returns[strategy_id].pop(0)
            
        except Exception as e:
            logger.error(f"❌ Error updating analytics data: {e}")
    
    def calculate_sharpe_ratio(self, returns: List[float], periods_per_year: int = 252) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        try:
            returns_array = np.array(returns)
            excess_returns = returns_array - (self.risk_free_rate / periods_per_year)
            
            if np.std(excess_returns) == 0:
                return 0.0
            
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(periods_per_year)
            return float(sharpe)
            
        except Exception as e:
            logger.error(f"❌ Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def calculate_sortino_ratio(self, returns: List[float], periods_per_year: int = 252) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if len(returns) < 2:
            return 0.0
        
        try:
            returns_array = np.array(returns)
            excess_returns = returns_array - (self.risk_free_rate / periods_per_year)
            
            # Calculate downside deviation
            negative_returns = excess_returns[excess_returns < 0]
            if len(negative_returns) == 0:
                return float('inf')  # No downside
            
            downside_deviation = np.sqrt(np.mean(negative_returns ** 2))
            if downside_deviation == 0:
                return 0.0
            
            sortino = np.mean(excess_returns) / downside_deviation * np.sqrt(periods_per_year)
            return float(sortino)
            
        except Exception as e:
            logger.error(f"❌ Error calculating Sortino ratio: {e}")
            return 0.0
    
    def calculate_max_drawdown(self, values: List[float]) -> Tuple[float, int, int]:
        """Calculate maximum drawdown and duration"""
        if len(values) < 2:
            return 0.0, 0, 0
        
        try:
            values_array = np.array(values)
            peak = np.maximum.accumulate(values_array)
            drawdown = (peak - values_array) / peak
            
            max_dd = np.max(drawdown)
            max_dd_idx = np.argmax(drawdown)
            
            # Find drawdown duration
            peak_idx = np.argmax(peak[:max_dd_idx + 1])
            duration = max_dd_idx - peak_idx
            
            return float(max_dd), int(peak_idx), int(duration)
            
        except Exception as e:
            logger.error(f"❌ Error calculating max drawdown: {e}")
            return 0.0, 0, 0
    
    def calculate_volatility(self, returns: List[float], periods_per_year: int = 252) -> float:
        """Calculate annualized volatility"""
        if len(returns) < 2:
            return 0.0
        
        try:
            returns_array = np.array(returns)
            volatility = np.std(returns_array) * np.sqrt(periods_per_year)
            return float(volatility)
            
        except Exception as e:
            logger.error(f"❌ Error calculating volatility: {e}")
            return 0.0
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if len(returns) < 10:  # Need sufficient data
            return 0.0
        
        try:
            returns_array = np.array(returns)
            var = np.percentile(returns_array, (1 - confidence) * 100)
            return float(var)
            
        except Exception as e:
            logger.error(f"❌ Error calculating VaR: {e}")
            return 0.0
    
    def calculate_strategy_correlation(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between strategies"""
        correlation_matrix = {}
        
        try:
            strategy_ids = list(self.strategy_returns.keys())
            
            for i, strategy1 in enumerate(strategy_ids):
                correlation_matrix[strategy1] = {}
                
                for j, strategy2 in enumerate(strategy_ids):
                    if i == j:
                        correlation_matrix[strategy1][strategy2] = 1.0
                    else:
                        returns1 = self.strategy_returns[strategy1]
                        returns2 = self.strategy_returns[strategy2]
                        
                        if len(returns1) >= 10 and len(returns2) >= 10:
                            # Align lengths
                            min_len = min(len(returns1), len(returns2))
                            r1 = np.array(returns1[-min_len:])
                            r2 = np.array(returns2[-min_len:])
                            
                            correlation = np.corrcoef(r1, r2)[0, 1]
                            if np.isnan(correlation):
                                correlation = 0.0
                            
                            correlation_matrix[strategy1][strategy2] = float(correlation)
                        else:
                            correlation_matrix[strategy1][strategy2] = 0.0
            
        except Exception as e:
            logger.error(f"❌ Error calculating strategy correlation: {e}")
        
        return correlation_matrix
    
    def calculate_performance_attribution(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance attribution by strategy"""
        attribution = {}
        
        try:
            total_portfolio_return = 0.0
            if len(self.portfolio_history) >= 2:
                total_portfolio_return = (self.portfolio_history[-1] - self.portfolio_history[0]) / self.portfolio_history[0]
            
            for strategy_id, returns in self.strategy_returns.items():
                if len(returns) >= 2:
                    strategy_return = sum(returns)
                    allocation = self.strategy_allocations.get(strategy_id, 0.0)
                    
                    # Calculate contribution to total return
                    contribution = strategy_return * allocation
                    
                    attribution[strategy_id] = {
                        'strategy_return': strategy_return,
                        'allocation': allocation,
                        'contribution': contribution,
                        'excess_return': strategy_return - total_portfolio_return
                    }
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance attribution: {e}")
        
        return attribution
    
    def calculate_risk_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        risk_metrics = {}
        
        try:
            if len(self.portfolio_history) < 2:
                return risk_metrics
            
            # Calculate portfolio returns
            portfolio_returns = []
            for i in range(1, len(self.portfolio_history)):
                ret = (self.portfolio_history[i] - self.portfolio_history[i-1]) / self.portfolio_history[i-1]
                portfolio_returns.append(ret)
            
            if len(portfolio_returns) < 2:
                return risk_metrics
            
            # Calculate metrics
            risk_metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(portfolio_returns)
            risk_metrics['sortino_ratio'] = self.calculate_sortino_ratio(portfolio_returns)
            risk_metrics['volatility'] = self.calculate_volatility(portfolio_returns)
            risk_metrics['var_95'] = self.calculate_var(portfolio_returns, 0.95)
            risk_metrics['var_99'] = self.calculate_var(portfolio_returns, 0.99)
            
            # Max drawdown
            max_dd, peak_idx, duration = self.calculate_max_drawdown(self.portfolio_history)
            risk_metrics['max_drawdown'] = max_dd
            risk_metrics['max_drawdown_duration'] = duration
            
            # Current drawdown
            if len(self.portfolio_history) > 0:
                current_value = self.portfolio_history[-1]
                peak_value = max(self.portfolio_history)
                current_drawdown = (peak_value - current_value) / peak_value if peak_value > 0 else 0.0
                risk_metrics['current_drawdown'] = current_drawdown
            
            # Win rate and profit factor
            winning_periods = sum(1 for r in portfolio_returns if r > 0)
            losing_periods = sum(1 for r in portfolio_returns if r < 0)
            
            risk_metrics['win_rate'] = winning_periods / len(portfolio_returns) if len(portfolio_returns) > 0 else 0.0
            
            # Profit factor
            gross_profit = sum(r for r in portfolio_returns if r > 0)
            gross_loss = abs(sum(r for r in portfolio_returns if r < 0))
            risk_metrics['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
        except Exception as e:
            logger.error(f"❌ Error calculating risk metrics: {e}")
        
        return risk_metrics
    
    def calculate_strategy_metrics(self) -> Dict[str, Dict[str, float]]:
        """Calculate metrics for each strategy"""
        strategy_metrics = {}
        
        try:
            for strategy_id, returns in self.strategy_returns.items():
                if len(returns) < 2:
                    continue
                
                metrics = {}
                metrics['total_return'] = sum(returns)
                metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(returns)
                metrics['sortino_ratio'] = self.calculate_sortino_ratio(returns)
                metrics['volatility'] = self.calculate_volatility(returns)
                metrics['var_95'] = self.calculate_var(returns, 0.95)
                
                # Win rate
                winning_periods = sum(1 for r in returns if r > 0)
                metrics['win_rate'] = winning_periods / len(returns)
                
                # Max drawdown (simplified for returns)
                cumulative_returns = np.cumprod([1 + r for r in returns])
                max_dd, _, duration = self.calculate_max_drawdown(cumulative_returns.tolist())
                metrics['max_drawdown'] = max_dd
                metrics['max_drawdown_duration'] = duration
                
                strategy_metrics[strategy_id] = metrics
                
        except Exception as e:
            logger.error(f"❌ Error calculating strategy metrics: {e}")
        
        return strategy_metrics
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'portfolio_metrics': self.calculate_risk_metrics(),
                'strategy_metrics': self.calculate_strategy_metrics(),
                'strategy_correlation': self.calculate_strategy_correlation(),
                'performance_attribution': self.calculate_performance_attribution(),
                'data_points': len(self.portfolio_history)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating analytics summary: {e}")
            return {}
    
    def get_real_time_alerts(self) -> List[Dict[str, Any]]:
        """Generate real-time risk alerts"""
        alerts = []
        
        try:
            risk_metrics = self.calculate_risk_metrics()
            
            # Drawdown alerts
            current_dd = risk_metrics.get('current_drawdown', 0.0)
            if current_dd > 0.05:  # 5% drawdown
                severity = 'HIGH' if current_dd > 0.08 else 'MEDIUM'
                alerts.append({
                    'type': 'DRAWDOWN',
                    'severity': severity,
                    'message': f'Portfolio drawdown at {current_dd:.2%}',
                    'value': current_dd,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Volatility alerts
            volatility = risk_metrics.get('volatility', 0.0)
            if volatility > 0.25:  # 25% annual volatility
                alerts.append({
                    'type': 'VOLATILITY',
                    'severity': 'MEDIUM',
                    'message': f'High portfolio volatility: {volatility:.2%}',
                    'value': volatility,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Strategy correlation alerts
            correlations = self.calculate_strategy_correlation()
            for strategy1, corr_dict in correlations.items():
                for strategy2, correlation in corr_dict.items():
                    if strategy1 != strategy2 and abs(correlation) > 0.8:
                        alerts.append({
                            'type': 'CORRELATION',
                            'severity': 'LOW',
                            'message': f'High correlation between {strategy1} and {strategy2}: {correlation:.2f}',
                            'value': correlation,
                            'timestamp': datetime.now().isoformat()
                        })
            
        except Exception as e:
            logger.error(f"❌ Error generating alerts: {e}")
        
        return alerts
