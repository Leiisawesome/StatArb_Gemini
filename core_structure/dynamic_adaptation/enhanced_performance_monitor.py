#!/usr/bin/env python3
"""
Enhanced Performance Monitor for Dynamic Adaptation
==================================================

Real-time performance monitoring and analysis for multi-strategy systems with:
- Strategy-specific performance tracking
- Cross-strategy performance comparison
- Performance degradation detection
- Market regime-aware performance analysis
- Adaptive performance thresholds

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class PerformanceRegime(Enum):
    """Performance regime classifications"""
    EXCELLENT = "excellent"      # Top quartile performance
    GOOD = "good"               # Above average performance
    AVERAGE = "average"         # Average performance
    POOR = "poor"              # Below average performance
    CRITICAL = "critical"       # Bottom quartile performance

class AlertLevel(Enum):
    """Performance alert levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    timestamp: datetime
    strategy_id: str
    
    # Return metrics
    total_return: float = 0.0
    daily_return: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    
    # Risk-adjusted metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Trading metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    
    # Portfolio metrics
    portfolio_value: float = 0.0
    cash_balance: float = 0.0
    position_count: int = 0
    
    # Performance regime
    regime: PerformanceRegime = PerformanceRegime.AVERAGE
    regime_confidence: float = 0.0

@dataclass
class PerformanceAlert:
    """Performance alert"""
    timestamp: datetime
    strategy_id: str
    alert_level: AlertLevel
    alert_type: str
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)

class EnhancedPerformanceMonitor:
    """
    Enhanced performance monitor for multi-strategy dynamic adaptation
    """
    
    def __init__(self, lookback_periods: int = 252):
        self.lookback_periods = lookback_periods
        self.strategy_metrics = defaultdict(lambda: deque(maxlen=lookback_periods))
        self.strategy_returns = defaultdict(lambda: deque(maxlen=lookback_periods))
        self.strategy_alerts = defaultdict(list)
        self.performance_thresholds = self._initialize_thresholds()
        self.regime_detector = None
        
        # Performance tracking
        self.last_update = {}
        self.performance_history = defaultdict(list)
        
    def _initialize_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize adaptive performance thresholds"""
        return {
            'return_thresholds': {
                'excellent': 0.15,    # 15%+ annual return
                'good': 0.08,         # 8%+ annual return
                'average': 0.03,      # 3%+ annual return
                'poor': -0.05,        # -5% annual return
                'critical': -0.15     # -15% annual return
            },
            'sharpe_thresholds': {
                'excellent': 2.0,
                'good': 1.5,
                'average': 1.0,
                'poor': 0.5,
                'critical': 0.0
            },
            'drawdown_thresholds': {
                'excellent': -0.05,   # Max 5% drawdown
                'good': -0.10,        # Max 10% drawdown
                'average': -0.15,     # Max 15% drawdown
                'poor': -0.25,        # Max 25% drawdown
                'critical': -0.35     # Max 35% drawdown
            },
            'volatility_thresholds': {
                'excellent': 0.10,    # Max 10% volatility
                'good': 0.15,         # Max 15% volatility
                'average': 0.20,      # Max 20% volatility
                'poor': 0.30,         # Max 30% volatility
                'critical': 0.50      # Max 50% volatility
            }
        }
    
    async def update_performance(
        self, 
        strategy_id: str, 
        portfolio_value: float,
        cash_balance: float,
        positions: Dict[str, Any],
        trades: List[Dict[str, Any]] = None
    ) -> PerformanceMetrics:
        """Update performance metrics for a strategy"""
        try:
            timestamp = datetime.now()
            
            # Calculate returns
            returns = await self._calculate_returns(strategy_id, portfolio_value)
            
            # Calculate risk metrics
            risk_metrics = await self._calculate_risk_metrics(strategy_id, returns)
            
            # Calculate trading metrics
            trading_metrics = await self._calculate_trading_metrics(strategy_id, trades or [])
            
            # Determine performance regime
            regime, confidence = await self._determine_performance_regime(
                strategy_id, returns, risk_metrics
            )
            
            # Create performance metrics
            metrics = PerformanceMetrics(
                timestamp=timestamp,
                strategy_id=strategy_id,
                total_return=returns.get('total_return', 0.0),
                daily_return=returns.get('daily_return', 0.0),
                annualized_return=returns.get('annualized_return', 0.0),
                volatility=risk_metrics.get('volatility', 0.0),
                max_drawdown=risk_metrics.get('max_drawdown', 0.0),
                var_95=risk_metrics.get('var_95', 0.0),
                sharpe_ratio=risk_metrics.get('sharpe_ratio', 0.0),
                sortino_ratio=risk_metrics.get('sortino_ratio', 0.0),
                calmar_ratio=risk_metrics.get('calmar_ratio', 0.0),
                win_rate=trading_metrics.get('win_rate', 0.0),
                profit_factor=trading_metrics.get('profit_factor', 0.0),
                avg_win=trading_metrics.get('avg_win', 0.0),
                avg_loss=trading_metrics.get('avg_loss', 0.0),
                portfolio_value=portfolio_value,
                cash_balance=cash_balance,
                position_count=len(positions),
                regime=regime,
                regime_confidence=confidence
            )
            
            # Store metrics
            self.strategy_metrics[strategy_id].append(metrics)
            self.last_update[strategy_id] = timestamp
            
            # Check for alerts
            alerts = await self._check_performance_alerts(strategy_id, metrics)
            self.strategy_alerts[strategy_id].extend(alerts)
            
            # Store in history for analysis
            self.performance_history[strategy_id].append({
                'timestamp': timestamp,
                'metrics': metrics,
                'alerts': alerts
            })
            
            logger.debug(f"📊 Performance updated for {strategy_id}: {regime.value} regime")
            return metrics
            
        except Exception as e:
            logger.error(f"Error updating performance for {strategy_id}: {e}")
            raise
    
    async def _calculate_returns(
        self, 
        strategy_id: str, 
        current_value: float
    ) -> Dict[str, float]:
        """Calculate return metrics"""
        try:
            returns = {}
            
            # Get historical values
            historical_metrics = list(self.strategy_metrics[strategy_id])
            
            if not historical_metrics:
                # First data point
                returns = {
                    'total_return': 0.0,
                    'daily_return': 0.0,
                    'annualized_return': 0.0
                }
            else:
                # Calculate returns
                initial_value = historical_metrics[0].portfolio_value
                previous_value = historical_metrics[-1].portfolio_value
                
                # Total return
                if initial_value > 0:
                    returns['total_return'] = (current_value - initial_value) / initial_value
                else:
                    returns['total_return'] = 0.0
                
                # Daily return
                if previous_value > 0:
                    returns['daily_return'] = (current_value - previous_value) / previous_value
                else:
                    returns['daily_return'] = 0.0
                
                # Annualized return
                days_elapsed = len(historical_metrics)
                if days_elapsed > 0:
                    returns['annualized_return'] = returns['total_return'] * (252 / days_elapsed)
                else:
                    returns['annualized_return'] = 0.0
            
            # Store daily return for volatility calculation
            self.strategy_returns[strategy_id].append(returns['daily_return'])
            
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return {'total_return': 0.0, 'daily_return': 0.0, 'annualized_return': 0.0}
    
    async def _calculate_risk_metrics(
        self, 
        strategy_id: str, 
        returns: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate risk metrics"""
        try:
            risk_metrics = {}
            
            # Get return series
            return_series = list(self.strategy_returns[strategy_id])
            
            if len(return_series) < 2:
                return {
                    'volatility': 0.0,
                    'max_drawdown': 0.0,
                    'var_95': 0.0,
                    'sharpe_ratio': 0.0,
                    'sortino_ratio': 0.0,
                    'calmar_ratio': 0.0
                }
            
            # Volatility (annualized)
            daily_vol = np.std(return_series)
            risk_metrics['volatility'] = daily_vol * np.sqrt(252)
            
            # Maximum drawdown
            cumulative_returns = np.cumprod(1 + np.array(return_series))
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            risk_metrics['max_drawdown'] = np.min(drawdowns)
            
            # Value at Risk (95%)
            risk_metrics['var_95'] = np.percentile(return_series, 5)
            
            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02 / 252  # Daily risk-free rate
            excess_returns = np.array(return_series) - risk_free_rate
            if daily_vol > 0:
                risk_metrics['sharpe_ratio'] = np.mean(excess_returns) / daily_vol * np.sqrt(252)
            else:
                risk_metrics['sharpe_ratio'] = 0.0
            
            # Sortino ratio
            negative_returns = [r for r in return_series if r < 0]
            if negative_returns:
                downside_vol = np.std(negative_returns)
                if downside_vol > 0:
                    risk_metrics['sortino_ratio'] = np.mean(excess_returns) / downside_vol * np.sqrt(252)
                else:
                    risk_metrics['sortino_ratio'] = 0.0
            else:
                risk_metrics['sortino_ratio'] = risk_metrics['sharpe_ratio']
            
            # Calmar ratio
            if risk_metrics['max_drawdown'] < 0:
                risk_metrics['calmar_ratio'] = returns['annualized_return'] / abs(risk_metrics['max_drawdown'])
            else:
                risk_metrics['calmar_ratio'] = 0.0
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'var_95': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0
            }
    
    async def _calculate_trading_metrics(
        self, 
        strategy_id: str, 
        trades: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate trading-specific metrics"""
        try:
            if not trades:
                return {
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0
                }
            
            # Extract P&L from trades
            pnls = []
            for trade in trades:
                if 'pnl' in trade:
                    pnls.append(trade['pnl'])
                elif 'realized_pnl' in trade:
                    pnls.append(trade['realized_pnl'])
            
            if not pnls:
                return {
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0
                }
            
            # Calculate metrics
            wins = [pnl for pnl in pnls if pnl > 0]
            losses = [pnl for pnl in pnls if pnl < 0]
            
            win_rate = len(wins) / len(pnls) if pnls else 0.0
            avg_win = np.mean(wins) if wins else 0.0
            avg_loss = np.mean(losses) if losses else 0.0
            
            # Profit factor
            total_wins = sum(wins) if wins else 0.0
            total_losses = abs(sum(losses)) if losses else 0.0
            profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
            
            return {
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            }
            
        except Exception as e:
            logger.error(f"Error calculating trading metrics: {e}")
            return {
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
    
    async def _determine_performance_regime(
        self, 
        strategy_id: str, 
        returns: Dict[str, float], 
        risk_metrics: Dict[str, float]
    ) -> Tuple[PerformanceRegime, float]:
        """Determine performance regime with confidence"""
        try:
            # Score different aspects
            return_score = self._score_metric(
                returns['annualized_return'], 
                self.performance_thresholds['return_thresholds']
            )
            
            sharpe_score = self._score_metric(
                risk_metrics['sharpe_ratio'], 
                self.performance_thresholds['sharpe_thresholds']
            )
            
            drawdown_score = self._score_metric(
                risk_metrics['max_drawdown'], 
                self.performance_thresholds['drawdown_thresholds'],
                reverse=True  # Lower drawdown is better
            )
            
            volatility_score = self._score_metric(
                risk_metrics['volatility'], 
                self.performance_thresholds['volatility_thresholds'],
                reverse=True  # Lower volatility is better
            )
            
            # Weighted average score
            weights = {'return': 0.3, 'sharpe': 0.3, 'drawdown': 0.2, 'volatility': 0.2}
            overall_score = (
                return_score * weights['return'] +
                sharpe_score * weights['sharpe'] +
                drawdown_score * weights['drawdown'] +
                volatility_score * weights['volatility']
            )
            
            # Determine regime
            if overall_score >= 4.0:
                regime = PerformanceRegime.EXCELLENT
            elif overall_score >= 3.0:
                regime = PerformanceRegime.GOOD
            elif overall_score >= 2.0:
                regime = PerformanceRegime.AVERAGE
            elif overall_score >= 1.0:
                regime = PerformanceRegime.POOR
            else:
                regime = PerformanceRegime.CRITICAL
            
            # Confidence based on consistency of scores
            score_variance = np.var([return_score, sharpe_score, drawdown_score, volatility_score])
            confidence = max(0.0, min(1.0, 1.0 - score_variance / 2.0))
            
            return regime, confidence
            
        except Exception as e:
            logger.error(f"Error determining performance regime: {e}")
            return PerformanceRegime.AVERAGE, 0.5
    
    def _score_metric(
        self, 
        value: float, 
        thresholds: Dict[str, float], 
        reverse: bool = False
    ) -> float:
        """Score a metric against thresholds"""
        try:
            if reverse:
                # For metrics where lower is better (drawdown, volatility)
                if value <= thresholds['excellent']:
                    return 5.0
                elif value <= thresholds['good']:
                    return 4.0
                elif value <= thresholds['average']:
                    return 3.0
                elif value <= thresholds['poor']:
                    return 2.0
                else:
                    return 1.0
            else:
                # For metrics where higher is better (return, sharpe)
                if value >= thresholds['excellent']:
                    return 5.0
                elif value >= thresholds['good']:
                    return 4.0
                elif value >= thresholds['average']:
                    return 3.0
                elif value >= thresholds['poor']:
                    return 2.0
                else:
                    return 1.0
                    
        except Exception as e:
            logger.error(f"Error scoring metric: {e}")
            return 3.0  # Default to average
    
    async def _check_performance_alerts(
        self, 
        strategy_id: str, 
        metrics: PerformanceMetrics
    ) -> List[PerformanceAlert]:
        """Check for performance alerts"""
        alerts = []
        
        try:
            # Critical performance alert
            if metrics.regime == PerformanceRegime.CRITICAL:
                alerts.append(PerformanceAlert(
                    timestamp=metrics.timestamp,
                    strategy_id=strategy_id,
                    alert_level=AlertLevel.CRITICAL,
                    alert_type="performance_critical",
                    message=f"Strategy performance is CRITICAL: {metrics.annualized_return:.2%} return, {metrics.sharpe_ratio:.2f} Sharpe",
                    metrics={
                        'annualized_return': metrics.annualized_return,
                        'sharpe_ratio': metrics.sharpe_ratio,
                        'max_drawdown': metrics.max_drawdown
                    },
                    recommended_actions=[
                        "Consider parameter optimization",
                        "Review strategy logic",
                        "Reduce position sizes",
                        "Consider strategy pause"
                    ]
                ))
            
            # Drawdown alert
            if metrics.max_drawdown < -0.20:  # 20% drawdown
                alerts.append(PerformanceAlert(
                    timestamp=metrics.timestamp,
                    strategy_id=strategy_id,
                    alert_level=AlertLevel.WARNING,
                    alert_type="high_drawdown",
                    message=f"High drawdown detected: {metrics.max_drawdown:.2%}",
                    metrics={'max_drawdown': metrics.max_drawdown},
                    recommended_actions=[
                        "Review risk management",
                        "Consider stop-loss adjustments",
                        "Reduce position sizes"
                    ]
                ))
            
            # Low Sharpe ratio alert
            if metrics.sharpe_ratio < 0.5:
                alerts.append(PerformanceAlert(
                    timestamp=metrics.timestamp,
                    strategy_id=strategy_id,
                    alert_level=AlertLevel.INFO,
                    alert_type="low_sharpe",
                    message=f"Low Sharpe ratio: {metrics.sharpe_ratio:.2f}",
                    metrics={'sharpe_ratio': metrics.sharpe_ratio},
                    recommended_actions=[
                        "Review entry/exit criteria",
                        "Consider parameter tuning",
                        "Analyze market conditions"
                    ]
                ))
            
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
        
        return alerts
    
    async def get_strategy_performance(self, strategy_id: str) -> Optional[PerformanceMetrics]:
        """Get latest performance metrics for a strategy"""
        if strategy_id in self.strategy_metrics and self.strategy_metrics[strategy_id]:
            return self.strategy_metrics[strategy_id][-1]
        return None
    
    async def get_performance_comparison(self) -> Dict[str, Any]:
        """Get performance comparison across all strategies"""
        try:
            comparison = {
                'timestamp': datetime.now(),
                'strategies': {},
                'rankings': {},
                'summary': {}
            }
            
            # Get latest metrics for each strategy
            strategy_performances = {}
            for strategy_id in self.strategy_metrics:
                if self.strategy_metrics[strategy_id]:
                    latest_metrics = self.strategy_metrics[strategy_id][-1]
                    strategy_performances[strategy_id] = latest_metrics
                    
                    comparison['strategies'][strategy_id] = {
                        'regime': latest_metrics.regime.value,
                        'annualized_return': latest_metrics.annualized_return,
                        'sharpe_ratio': latest_metrics.sharpe_ratio,
                        'max_drawdown': latest_metrics.max_drawdown,
                        'win_rate': latest_metrics.win_rate,
                        'profit_factor': latest_metrics.profit_factor
                    }
            
            # Create rankings
            if strategy_performances:
                # Rank by Sharpe ratio
                sharpe_ranking = sorted(
                    strategy_performances.items(),
                    key=lambda x: x[1].sharpe_ratio,
                    reverse=True
                )
                comparison['rankings']['sharpe_ratio'] = [s[0] for s in sharpe_ranking]
                
                # Rank by return
                return_ranking = sorted(
                    strategy_performances.items(),
                    key=lambda x: x[1].annualized_return,
                    reverse=True
                )
                comparison['rankings']['annualized_return'] = [s[0] for s in return_ranking]
                
                # Summary statistics
                returns = [m.annualized_return for m in strategy_performances.values()]
                sharpes = [m.sharpe_ratio for m in strategy_performances.values()]
                
                comparison['summary'] = {
                    'total_strategies': len(strategy_performances),
                    'avg_return': np.mean(returns),
                    'avg_sharpe': np.mean(sharpes),
                    'best_performer': sharpe_ranking[0][0] if sharpe_ranking else None,
                    'worst_performer': sharpe_ranking[-1][0] if sharpe_ranking else None
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error creating performance comparison: {e}")
            return {'error': str(e)}
    
    async def get_active_alerts(self, strategy_id: Optional[str] = None) -> List[PerformanceAlert]:
        """Get active performance alerts"""
        if strategy_id:
            return self.strategy_alerts.get(strategy_id, [])
        else:
            # Return all alerts
            all_alerts = []
            for alerts in self.strategy_alerts.values():
                all_alerts.extend(alerts)
            return sorted(all_alerts, key=lambda x: x.timestamp, reverse=True)
