"""
AnalyticsBridge: Core System ↔ Backtesting Framework Integration

This module provides a bridge between the core system's analytics capabilities
and the backtesting framework's analytics requirements.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
from enum import Enum

logger = logging.getLogger(__name__)


class AnalyticsMode(Enum):
    """Analytics bridge operation modes"""
    PRODUCTION = "production"
    BACKTESTING = "backtesting"
    SIMULATION = "simulation"
    PAPER_TRADING = "paper_trading"


class AnalyticsStatus(Enum):
    """Analytics status levels"""
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AnalyticsBridgeConfig:
    """Configuration for AnalyticsBridge"""
    analytics_mode: AnalyticsMode = AnalyticsMode.BACKTESTING
    enable_performance_analytics: bool = True
    enable_risk_analytics: bool = True
    enable_signal_analytics: bool = True
    enable_portfolio_analytics: bool = True
    max_concurrent_operations: int = 10
    timeout_seconds: float = 30.0
    cache_size: int = 1000
    analytics_window: int = 252  # Trading days
    confidence_level: float = 0.95


@dataclass
class AnalyticsBridgeResult:
    """Result from AnalyticsBridge operations"""
    operation_type: str
    analytics_id: str
    data: Union[pd.DataFrame, Dict[str, Any]]
    success: bool
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class AnalyticsSnapshot:
    """Analytics snapshot with current state"""
    analytics_id: str
    analytics_type: str
    analytics_data: Dict[str, Any]
    status: AnalyticsStatus
    last_updated: datetime
    version: str
    environment: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceMetrics:
    """Performance metrics for analytics"""
    total_return: float
    total_return_pct: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float


@dataclass
class RiskMetrics:
    """Risk metrics for analytics"""
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    volatility: float
    beta: float
    correlation: float
    max_drawdown: float
    max_drawdown_pct: float
    downside_deviation: float
    skewness: float
    kurtosis: float


class AnalyticsBridge:
    """Bridge between core system analytics and backtesting framework."""
    
    def __init__(self, config: Optional[AnalyticsBridgeConfig] = None):
        """Initialize AnalyticsBridge with configuration"""
        self.config = config or AnalyticsBridgeConfig()
        self.logger = logging.getLogger(f"{__name__}.AnalyticsBridge")
        
        # Initialize caching and performance tracking
        self._analytics_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._performance_stats = {
            'total_operations': 0,
            'production_operations': 0,
            'backtesting_operations': 0,
            'cached_operations': 0,
            'errors': 0,
            'avg_processing_time': 0.0,
            'total_analytics': 0
        }
        
        # Thread pool for concurrent operations
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_operations)
        
        self.logger.info(f"AnalyticsBridge initialized in {self.config.analytics_mode.value} mode")
    
    async def get_analytics_snapshot(self, analytics_id: str) -> AnalyticsSnapshot:
        """Get current analytics snapshot"""
        start_time_ms = time.time()
        
        try:
            # Check cache first
            cache_key = f"analytics_{analytics_id}"
            if cache_key in self._analytics_cache:
                cached_data, cache_time = self._analytics_cache[cache_key]
                if datetime.now() - cache_time < timedelta(minutes=10):  # 10-minute cache
                    self._performance_stats['cached_operations'] += 1
                    return cached_data
            
            # Create analytics snapshot
            snapshot = self._create_analytics_snapshot(analytics_id)
            
            # Cache the result
            self._analytics_cache[cache_key] = (snapshot, datetime.now())
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Error getting analytics snapshot for {analytics_id}: {e}")
            self._performance_stats['errors'] += 1
            return self._create_fallback_snapshot(analytics_id)
    
    async def calculate_performance_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None
    ) -> PerformanceMetrics:
        """Calculate performance metrics"""
        start_time_ms = time.time()
        
        try:
            # Calculate basic metrics
            total_return = (1 + returns).prod() - 1
            total_return_pct = total_return * 100
            
            # Annualized return
            trading_days = len(returns)
            annualized_return = (1 + total_return) ** (252 / trading_days) - 1
            
            # Volatility
            volatility = returns.std() * np.sqrt(252)
            
            # Sharpe ratio
            risk_free_rate = 0.02  # 2% annual risk-free rate
            excess_returns = returns - risk_free_rate / 252
            sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
            
            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            max_drawdown_pct = max_drawdown * 100
            
            # Win rate
            win_rate = (returns > 0).mean()
            
            # Profit factor
            gains = returns[returns > 0].sum()
            losses = abs(returns[returns < 0].sum())
            profit_factor = gains / losses if losses != 0 else float('inf')
            
            # Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Sortino ratio
            downside_returns = returns[returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(252)
            sortino_ratio = excess_returns.mean() / downside_deviation * np.sqrt(252) if downside_deviation != 0 else 0
            
            # Beta and Alpha (if benchmark provided)
            beta = 1.0
            alpha = 0.0
            information_ratio = 0.0
            tracking_error = 0.0
            
            if benchmark_returns is not None:
                # Beta
                covariance = np.cov(returns, benchmark_returns)[0, 1]
                benchmark_variance = benchmark_returns.var()
                beta = covariance / benchmark_variance if benchmark_variance != 0 else 1.0
                
                # Alpha
                benchmark_annualized = (1 + benchmark_returns).prod() ** (252 / len(benchmark_returns)) - 1
                alpha = annualized_return - (risk_free_rate + beta * (benchmark_annualized - risk_free_rate))
                
                # Information ratio
                active_returns = returns - benchmark_returns
                information_ratio = active_returns.mean() / active_returns.std() * np.sqrt(252)
                
                # Tracking error
                tracking_error = active_returns.std() * np.sqrt(252)
            
            return PerformanceMetrics(
                total_return=total_return,
                total_return_pct=total_return_pct,
                annualized_return=annualized_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                max_drawdown_pct=max_drawdown_pct,
                win_rate=win_rate,
                profit_factor=profit_factor,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio,
                beta=beta,
                alpha=alpha,
                information_ratio=information_ratio,
                tracking_error=tracking_error
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            raise
    
    async def calculate_risk_metrics(self, returns: pd.Series) -> RiskMetrics:
        """Calculate risk metrics"""
        start_time_ms = time.time()
        
        try:
            # VaR calculations
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)
            
            # CVaR calculations
            cvar_95 = returns[returns <= var_95].mean()
            cvar_99 = returns[returns <= var_99].mean()
            
            # Volatility
            volatility = returns.std() * np.sqrt(252)
            
            # Beta (assuming market beta of 1)
            beta = 1.0
            
            # Correlation (assuming market correlation)
            correlation = 0.5
            
            # Maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            max_drawdown_pct = max_drawdown * 100
            
            # Downside deviation
            downside_returns = returns[returns < 0]
            downside_deviation = downside_returns.std() * np.sqrt(252)
            
            # Skewness and Kurtosis
            skewness = returns.skew()
            kurtosis = returns.kurtosis()
            
            return RiskMetrics(
                var_95=var_95,
                var_99=var_99,
                cvar_95=cvar_95,
                cvar_99=cvar_99,
                volatility=volatility,
                beta=beta,
                correlation=correlation,
                max_drawdown=max_drawdown,
                max_drawdown_pct=max_drawdown_pct,
                downside_deviation=downside_deviation,
                skewness=skewness,
                kurtosis=kurtosis
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            raise
    
    async def generate_analytics_report(
        self,
        analytics_id: str,
        data: Dict[str, Any]
    ) -> AnalyticsBridgeResult:
        """Generate comprehensive analytics report"""
        start_time_ms = time.time()
        
        try:
            # Mock analytics report generation
            report = {
                'analytics_id': analytics_id,
                'timestamp': datetime.now(),
                'performance_metrics': {
                    'total_return': 0.15,
                    'annualized_return': 0.12,
                    'sharpe_ratio': 1.2,
                    'max_drawdown': -0.08
                },
                'risk_metrics': {
                    'var_95': -0.02,
                    'volatility': 0.18,
                    'beta': 1.1
                },
                'recommendations': [
                    'Consider reducing position sizes',
                    'Monitor drawdown levels',
                    'Review risk management parameters'
                ]
            }
            
            # Update performance stats
            self._update_performance_stats('backtesting', time.time() - start_time_ms)
            
            return AnalyticsBridgeResult(
                operation_type='analytics_report',
                analytics_id=analytics_id,
                data=report,
                success=True,
                timestamp=datetime.now(),
                source='backtesting',
                processing_time_ms=(time.time() - start_time_ms) * 1000
            )
            
        except Exception as e:
            self.logger.error(f"Error generating analytics report for {analytics_id}: {e}")
            self._performance_stats['errors'] += 1
            
            return AnalyticsBridgeResult(
                operation_type='analytics_report',
                analytics_id=analytics_id,
                data={},
                success=False,
                timestamp=datetime.now(),
                source='fallback',
                processing_time_ms=(time.time() - start_time_ms) * 1000,
                error_message=str(e)
            )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self._performance_stats.copy()
    
    def clear_cache(self) -> None:
        """Clear analytics cache"""
        self._analytics_cache.clear()
        self.logger.info("Analytics cache cleared")
    
    def _create_analytics_snapshot(self, analytics_id: str) -> AnalyticsSnapshot:
        """Create analytics snapshot"""
        # Get analytics type from ID
        analytics_type = analytics_id.split('_')[0] if '_' in analytics_id else 'performance'
        
        # Mock analytics data
        analytics_data = {
            'performance_metrics': {
                'total_return': 0.15,
                'annualized_return': 0.12,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08
            },
            'risk_metrics': {
                'var_95': -0.02,
                'volatility': 0.18,
                'beta': 1.1
            },
            'signal_metrics': {
                'signal_accuracy': 0.65,
                'signal_frequency': 0.1,
                'signal_strength': 0.7
            }
        }
        
        return AnalyticsSnapshot(
            analytics_id=analytics_id,
            analytics_type=analytics_type,
            analytics_data=analytics_data,
            status=AnalyticsStatus.COMPLETED,
            last_updated=datetime.now(),
            version='1.0.0',
            environment=self.config.analytics_mode.value
        )
    
    def _create_fallback_snapshot(self, analytics_id: str) -> AnalyticsSnapshot:
        """Create fallback analytics snapshot"""
        return AnalyticsSnapshot(
            analytics_id=analytics_id,
            analytics_type='fallback',
            analytics_data={},
            status=AnalyticsStatus.ERROR,
            last_updated=datetime.now(),
            version='0.0.0',
            environment='fallback'
        )
    
    def _update_performance_stats(self, source: str, processing_time: float):
        """Update performance statistics"""
        try:
            self._performance_stats['total_operations'] += 1
            self._performance_stats['total_analytics'] += 1
            
            if source == 'production':
                self._performance_stats['production_operations'] += 1
            elif source == 'backtesting':
                self._performance_stats['backtesting_operations'] += 1
            
            # Update average processing time
            total_operations = self._performance_stats['total_operations']
            current_avg = self._performance_stats['avg_processing_time']
            new_avg = ((current_avg * (total_operations - 1)) + processing_time) / total_operations
            self._performance_stats['avg_processing_time'] = new_avg
            
        except Exception as e:
            self.logger.error(f"Error updating performance stats: {e}")


def create_analytics_bridge(config: Optional[AnalyticsBridgeConfig] = None) -> AnalyticsBridge:
    """Factory function to create AnalyticsBridge instance"""
    return AnalyticsBridge(config)


def get_analytics_for_backtesting(analytics_id: str) -> AnalyticsSnapshot:
    """Convenience function for backtesting analytics retrieval"""
    config = AnalyticsBridgeConfig(analytics_mode=AnalyticsMode.BACKTESTING)
    bridge = create_analytics_bridge(config)
    
    # Check if there's already an event loop running
    try:
        loop = asyncio.get_running_loop()
        # Return fallback snapshot as fallback
        return AnalyticsSnapshot(
            analytics_id=analytics_id,
            analytics_type='fallback',
            analytics_data={},
            status=AnalyticsStatus.ERROR,
            last_updated=datetime.now(),
            version='0.0.0',
            environment='fallback'
        )
    except RuntimeError:
        # No event loop running, we can create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            snapshot = loop.run_until_complete(
                bridge.get_analytics_snapshot(analytics_id)
            )
            return snapshot
        finally:
            loop.close() 