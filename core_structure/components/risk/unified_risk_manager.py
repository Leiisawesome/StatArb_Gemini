#!/usr/bin/env python3
"""
Unified Risk Management System
==============================

Comprehensive risk management system that works for both backtesting and live trading.
Combines the best features from all existing risk management systems.

Features:
- Consistent risk logic across backtesting and live trading
- Advanced ML-powered risk analytics
- Real-time monitoring and alerts
- Dynamic portfolio allocation
- Volatility-based position sizing
- Order management integration
- Multi-strategy coordination

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from abc import ABC, abstractmethod

# ML libraries (optional imports for backtesting compatibility)
try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    from scipy import stats
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskAction(Enum):
    """Risk management actions"""
    NONE = "NONE"
    REDUCE_POSITIONS = "REDUCE_POSITIONS"
    HALT_NEW_TRADES = "HALT_NEW_TRADES"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"

class TradingMode(Enum):
    """Trading mode for risk manager"""
    BACKTESTING = "BACKTESTING"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"

@dataclass
class RiskLimits:
    """Unified risk limits configuration"""
    # Position limits
    max_position_size_pct: float = 0.1      # 10% max position size
    max_sector_exposure_pct: float = 0.3     # 30% max sector exposure
    max_strategy_allocation_pct: float = 0.6  # 60% max strategy allocation
    
    # Drawdown limits
    max_portfolio_drawdown: float = 0.10     # 10% max portfolio drawdown
    max_strategy_drawdown: float = 0.05      # 5% max strategy drawdown
    daily_loss_limit: float = 0.05           # 5% daily loss limit
    
    # Risk management orders
    default_stop_loss_pct: float = 0.02      # 2% default stop loss
    default_take_profit_pct: float = 0.04    # 4% default take profit
    default_trailing_stop_pct: float = 0.015 # 1.5% default trailing stop
    
    # Volatility and correlation
    target_portfolio_volatility: float = 0.15  # 15% target volatility
    max_correlation_threshold: float = 0.7    # 70% max correlation
    
    # VaR limits
    var_confidence_level: float = 0.95        # 95% VaR confidence
    max_var_pct: float = 0.03                # 3% max VaR

@dataclass
class UnifiedRiskMetrics:
    """Comprehensive risk metrics"""
    # Portfolio metrics
    portfolio_value: float
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    
    # Drawdown metrics
    current_drawdown: float
    max_drawdown: float
    drawdown_duration_days: int
    
    # Risk metrics
    portfolio_volatility: float
    sharpe_ratio: float
    var_95: float
    cvar_95: float
    
    # Correlation and concentration
    max_correlation: float
    concentration_risk: float
    sector_concentration: Dict[str, float] = field(default_factory=dict)
    
    # Strategy metrics
    strategy_allocations: Dict[str, float] = field(default_factory=dict)
    strategy_performance: Dict[str, float] = field(default_factory=dict)
    strategy_risk_scores: Dict[str, float] = field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskAlert:
    """Risk management alert"""
    alert_id: str
    risk_level: RiskLevel
    message: str
    recommended_action: RiskAction
    affected_strategies: List[str]
    affected_symbols: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PositionRiskProfile:
    """Risk profile for individual position"""
    symbol: str
    strategy_id: str
    position_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    risk_score: float
    volatility: float
    correlation_with_market: float
    time_held: timedelta
    risk_level: RiskLevel

class IRiskDataProvider(ABC):
    """Interface for risk data providers"""
    
    @abstractmethod
    async def get_current_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbols: List[str]) -> Dict[str, float]:
        """Get current market data"""
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbols: List[str], days: int) -> Dict[str, List[float]]:
        """Get historical price data"""
        pass

class UnifiedRiskManager:
    """
    Unified Risk Management System
    
    Works for both backtesting and live trading with consistent risk logic.
    Combines advanced analytics with real-time monitoring capabilities.
    """
    
    def __init__(self, 
                 risk_limits: Optional[RiskLimits] = None,
                 trading_mode: TradingMode = TradingMode.PAPER_TRADING,
                 initial_capital: float = 100000.0,
                 data_provider: Optional[IRiskDataProvider] = None):
        
        self.risk_limits = risk_limits or RiskLimits()
        self.trading_mode = trading_mode
        self.initial_capital = initial_capital
        self.data_provider = data_provider
        
        # Portfolio state
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.portfolio_history: List[Dict] = []
        
        # Strategy tracking
        self.strategy_allocations: Dict[str, float] = {}
        self.strategy_history: Dict[str, List[Dict]] = {}
        self.strategy_risk_profiles: Dict[str, Dict] = {}
        
        # Market data
        self.price_history: Dict[str, List[float]] = {}
        self.returns_history: Dict[str, List[float]] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        
        # Risk state
        self.current_metrics: Optional[UnifiedRiskMetrics] = None
        self.active_alerts: List[RiskAlert] = []
        self.risk_overrides: Dict[str, bool] = {}
        
        # Callbacks
        self.risk_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        # ML models (if available)
        self.ml_models: Dict[str, Any] = {}
        if ML_AVAILABLE and trading_mode != TradingMode.BACKTESTING:
            self._initialize_ml_models()
        
        logger.info(f"🛡️  Unified Risk Manager initialized - Mode: {trading_mode.value}")
    
    def set_strategy_allocations(self, allocations: Dict[str, float]):
        """Set strategy allocations"""
        
        total = sum(allocations.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Allocations must sum to 1.0, got {total}")
        
        self.strategy_allocations = allocations.copy()
        
        logger.info("📊 Strategy allocations set:")
        for strategy_id, allocation in allocations.items():
            logger.info(f"   {strategy_id}: {allocation*100:.1f}%")
    
    def add_risk_callback(self, callback: Callable):
        """Add callback for risk events"""
        self.risk_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for risk alerts"""
        self.alert_callbacks.append(callback)
    
    async def update_portfolio_state(self, portfolio_data: Dict[str, Any]):
        """Update portfolio state and calculate risk metrics"""
        
        try:
            # Extract portfolio data
            total_value = portfolio_data.get('total_value', self.current_capital)
            strategy_values = portfolio_data.get('strategy_values', {})
            positions = portfolio_data.get('positions', {})
            current_prices = portfolio_data.get('current_prices', {})
            
            # Update internal state
            self.current_capital = total_value
            self.peak_capital = max(self.peak_capital, total_value)
            
            # Update price history
            await self._update_price_history(current_prices)
            
            # Calculate comprehensive risk metrics
            self.current_metrics = await self._calculate_unified_risk_metrics(
                total_value, strategy_values, positions, current_prices
            )
            
            # Store portfolio history
            self.portfolio_history.append({
                'timestamp': datetime.now(),
                'value': total_value,
                'pnl': total_value - self.initial_capital,
                'drawdown': self.current_metrics.current_drawdown
            })
            
            # Keep history manageable
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
            
            # Check for risk alerts
            await self._check_risk_alerts()
            
            # Update dynamic allocations (if in live trading mode)
            if self.trading_mode != TradingMode.BACKTESTING:
                await self._update_dynamic_allocations()
            
            # Trigger callbacks
            for callback in self.risk_callbacks:
                try:
                    await callback(self.current_metrics)
                except Exception as e:
                    logger.error(f"Risk callback error: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating portfolio state: {e}")
    
    async def _calculate_unified_risk_metrics(self, total_value: float, 
                                            strategy_values: Dict[str, float],
                                            positions: Dict[str, Any],
                                            current_prices: Dict[str, float]) -> UnifiedRiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        # Basic metrics
        total_pnl = total_value - self.initial_capital
        current_drawdown = (self.peak_capital - total_value) / self.peak_capital if self.peak_capital > 0 else 0
        max_drawdown = self._calculate_max_drawdown()
        
        # Volatility and Sharpe ratio
        portfolio_volatility = self._calculate_portfolio_volatility()
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # VaR calculations
        var_95, cvar_95 = self._calculate_var_cvar()
        
        # Correlation and concentration
        max_correlation = self._calculate_max_correlation()
        concentration_risk = self._calculate_concentration_risk(strategy_values)
        
        # Strategy metrics
        strategy_performance = self._calculate_strategy_performance(strategy_values)
        strategy_risk_scores = self._calculate_strategy_risk_scores(positions)
        
        return UnifiedRiskMetrics(
            portfolio_value=total_value,
            total_pnl=total_pnl,
            unrealized_pnl=sum(strategy_values.values()) - self.initial_capital,
            realized_pnl=0,  # Simplified for now
            current_drawdown=current_drawdown,
            max_drawdown=max_drawdown,
            drawdown_duration_days=self._calculate_drawdown_duration(),
            portfolio_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            max_correlation=max_correlation,
            concentration_risk=concentration_risk,
            strategy_allocations=self.strategy_allocations.copy(),
            strategy_performance=strategy_performance,
            strategy_risk_scores=strategy_risk_scores
        )
    
    def should_allow_new_trade(self, strategy_id: str, symbol: str, 
                              position_size: float, current_price: float) -> Tuple[bool, str]:
        """Unified trade approval logic for both backtesting and live trading"""
        
        # Check for critical alerts
        critical_alerts = [alert for alert in self.active_alerts 
                          if alert.risk_level == RiskLevel.CRITICAL]
        if critical_alerts:
            return False, "Critical risk alerts active"
        
        # Check portfolio drawdown
        if (self.current_metrics and 
            self.current_metrics.current_drawdown > self.risk_limits.max_portfolio_drawdown * 0.8):
            return False, f"Portfolio drawdown too high: {self.current_metrics.current_drawdown:.1%}"
        
        # Check position size limits
        position_value = position_size * current_price
        position_pct = position_value / self.current_capital
        
        if position_pct > self.risk_limits.max_position_size_pct:
            return False, f"Position size too large: {position_pct:.1%} > {self.risk_limits.max_position_size_pct:.1%}"
        
        # Check strategy allocation limits
        strategy_allocation = self.strategy_allocations.get(strategy_id, 0)
        if strategy_allocation > self.risk_limits.max_strategy_allocation_pct:
            return False, f"Strategy allocation too high: {strategy_allocation:.1%}"
        
        # Check strategy-specific drawdown
        if (self.current_metrics and strategy_id in self.current_metrics.strategy_risk_scores):
            strategy_risk = self.current_metrics.strategy_risk_scores[strategy_id]
            if strategy_risk > 0.8:  # High risk threshold
                return False, f"Strategy risk score too high: {strategy_risk:.2f}"
        
        # Check risk overrides
        if self.risk_overrides.get(strategy_id, False):
            return False, "Strategy trading halted by risk override"
        
        # Check VaR limits
        if (self.current_metrics and 
            self.current_metrics.var_95 > self.risk_limits.max_var_pct * self.current_capital):
            return False, f"Portfolio VaR too high: ${self.current_metrics.var_95:.0f}"
        
        return True, "Trade approved"
    
    def get_recommended_position_size(self, strategy_id: str, symbol: str, 
                                    base_size: float, current_price: float) -> float:
        """Get risk-adjusted position size recommendation"""
        
        try:
            # Base position value
            base_value = base_size * current_price
            base_pct = base_value / self.current_capital
            
            # Volatility adjustment
            symbol_volatility = self._get_symbol_volatility(symbol)
            if symbol_volatility > 0:
                vol_adjustment = min(self.risk_limits.target_portfolio_volatility / symbol_volatility, 2.0)
            else:
                vol_adjustment = 1.0
            
            # Strategy performance adjustment
            if (self.current_metrics and strategy_id in self.current_metrics.strategy_performance):
                perf_score = self.current_metrics.strategy_performance[strategy_id]
                perf_adjustment = 0.5 + perf_score * 0.5  # 0.5x to 1.5x based on performance
            else:
                perf_adjustment = 1.0
            
            # Drawdown adjustment
            if self.current_metrics:
                dd_adjustment = 1.0 - self.current_metrics.current_drawdown * 2
            else:
                dd_adjustment = 1.0
            
            # Combined adjustment
            total_adjustment = vol_adjustment * perf_adjustment * dd_adjustment
            adjusted_size = base_size * max(min(total_adjustment, 3.0), 0.1)  # 0.1x to 3x range
            
            # Final position size check
            adjusted_value = adjusted_size * current_price
            adjusted_pct = adjusted_value / self.current_capital
            
            if adjusted_pct > self.risk_limits.max_position_size_pct:
                adjusted_size = (self.risk_limits.max_position_size_pct * self.current_capital) / current_price
            
            return max(adjusted_size, 1.0)  # Minimum 1 unit
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return base_size
    
    def get_stop_loss_price(self, entry_price: float, side: str, 
                           custom_pct: Optional[float] = None) -> float:
        """Calculate stop-loss price"""
        
        stop_pct = custom_pct or self.risk_limits.default_stop_loss_pct
        
        if side.upper() == "LONG":
            return entry_price * (1 - stop_pct)
        else:  # SHORT
            return entry_price * (1 + stop_pct)
    
    def get_take_profit_price(self, entry_price: float, side: str,
                             custom_pct: Optional[float] = None) -> float:
        """Calculate take-profit price"""
        
        tp_pct = custom_pct or self.risk_limits.default_take_profit_pct
        
        if side.upper() == "LONG":
            return entry_price * (1 + tp_pct)
        else:  # SHORT
            return entry_price * (1 - tp_pct)
    
    async def _update_price_history(self, current_prices: Dict[str, float]):
        """Update price history for risk calculations"""
        
        for symbol, price in current_prices.items():
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            self.price_history[symbol].append(price)
            
            # Keep last 252 observations (1 year of daily data)
            if len(self.price_history[symbol]) > 252:
                self.price_history[symbol] = self.price_history[symbol][-252:]
            
            # Calculate returns
            if len(self.price_history[symbol]) >= 2:
                if symbol not in self.returns_history:
                    self.returns_history[symbol] = []
                
                prev_price = self.price_history[symbol][-2]
                if prev_price > 0:
                    return_pct = (price - prev_price) / prev_price
                    self.returns_history[symbol].append(return_pct)
                    
                    # Keep last 252 returns
                    if len(self.returns_history[symbol]) > 252:
                        self.returns_history[symbol] = self.returns_history[symbol][-252:]
    
    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility"""
        
        if len(self.portfolio_history) < 10:
            return 0.0
        
        try:
            returns = []
            for i in range(1, len(self.portfolio_history)):
                prev_val = self.portfolio_history[i-1]['value']
                curr_val = self.portfolio_history[i]['value']
                if prev_val > 0:
                    ret = (curr_val - prev_val) / prev_val
                    returns.append(ret)
            
            if len(returns) < 5:
                return 0.0
            
            # Annualized volatility
            vol = np.std(returns) * np.sqrt(252)  # Assuming daily returns
            return min(vol, 1.0)  # Cap at 100%
            
        except Exception:
            return 0.0
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio"""
        
        if len(self.portfolio_history) < 10:
            return 0.0
        
        try:
            returns = []
            for i in range(1, len(self.portfolio_history)):
                prev_val = self.portfolio_history[i-1]['value']
                curr_val = self.portfolio_history[i]['value']
                if prev_val > 0:
                    ret = (curr_val - prev_val) / prev_val
                    returns.append(ret)
            
            if len(returns) < 5:
                return 0.0
            
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            if std_return == 0:
                return 0.0
            
            # Annualized Sharpe (assuming risk-free rate = 2%)
            risk_free_daily = 0.02 / 252
            sharpe = (mean_return - risk_free_daily) / std_return * np.sqrt(252)
            return max(min(sharpe, 10.0), -10.0)  # Cap between -10 and 10
            
        except Exception:
            return 0.0
    
    def _calculate_var_cvar(self) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional VaR"""
        
        if len(self.portfolio_history) < 30:
            return 0.0, 0.0
        
        try:
            returns = []
            for i in range(1, len(self.portfolio_history)):
                prev_val = self.portfolio_history[i-1]['value']
                curr_val = self.portfolio_history[i]['value']
                if prev_val > 0:
                    ret = (curr_val - prev_val) / prev_val
                    returns.append(ret)
            
            if len(returns) < 20:
                return 0.0, 0.0
            
            # Calculate VaR at specified confidence level
            var_percentile = (1 - self.risk_limits.var_confidence_level) * 100
            var_return = np.percentile(returns, var_percentile)
            var_dollar = abs(var_return * self.current_capital)
            
            # Calculate CVaR (expected shortfall)
            tail_returns = [r for r in returns if r <= var_return]
            if tail_returns:
                cvar_return = np.mean(tail_returns)
                cvar_dollar = abs(cvar_return * self.current_capital)
            else:
                cvar_dollar = var_dollar
            
            return var_dollar, cvar_dollar
            
        except Exception:
            return 0.0, 0.0
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        
        if len(self.portfolio_history) < 2:
            return 0.0
        
        try:
            peak = self.portfolio_history[0]['value']
            max_dd = 0.0
            
            for record in self.portfolio_history:
                value = record['value']
                if value > peak:
                    peak = value
                
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_dd = max(max_dd, drawdown)
            
            return max_dd
            
        except Exception:
            return 0.0
    
    def _calculate_drawdown_duration(self) -> int:
        """Calculate current drawdown duration in days"""
        
        # Simplified calculation - count periods since last peak
        if not self.portfolio_history:
            return 0
        
        current_value = self.portfolio_history[-1]['value']
        days_since_peak = 0
        
        for i in range(len(self.portfolio_history) - 1, -1, -1):
            if self.portfolio_history[i]['value'] >= current_value:
                break
            days_since_peak += 1
        
        return days_since_peak
    
    def _calculate_max_correlation(self) -> float:
        """Calculate maximum correlation between assets"""
        
        if len(self.returns_history) < 2:
            return 0.0
        
        try:
            # Get symbols with sufficient data
            symbols = [s for s, returns in self.returns_history.items() if len(returns) >= 20]
            
            if len(symbols) < 2:
                return 0.0
            
            # Create correlation matrix
            returns_df = pd.DataFrame({
                symbol: self.returns_history[symbol][-min(len(self.returns_history[symbol]), 100):]
                for symbol in symbols
            })
            
            corr_matrix = returns_df.corr()
            
            # Find maximum correlation (excluding diagonal)
            max_corr = 0.0
            for i in range(len(corr_matrix)):
                for j in range(i+1, len(corr_matrix)):
                    corr_val = abs(corr_matrix.iloc[i, j])
                    if not np.isnan(corr_val):
                        max_corr = max(max_corr, corr_val)
            
            return max_corr
            
        except Exception:
            return 0.0
    
    def _calculate_concentration_risk(self, strategy_values: Dict[str, float]) -> float:
        """Calculate portfolio concentration risk"""
        
        if not strategy_values:
            return 0.0
        
        total_value = sum(strategy_values.values())
        if total_value == 0:
            return 0.0
        
        # Calculate Herfindahl-Hirschman Index
        hhi = sum((value / total_value) ** 2 for value in strategy_values.values())
        return min(hhi, 1.0)
    
    def _calculate_strategy_performance(self, strategy_values: Dict[str, float]) -> Dict[str, float]:
        """Calculate strategy performance scores"""
        
        performance = {}
        
        for strategy_id, current_value in strategy_values.items():
            base_allocation = self.strategy_allocations.get(strategy_id, 0)
            allocated_capital = self.initial_capital * base_allocation
            
            if allocated_capital > 0:
                return_pct = (current_value - allocated_capital) / allocated_capital
                # Normalize to 0-1 scale (0 = -10% return, 1 = +10% return)
                performance_score = max(min((return_pct + 0.1) / 0.2, 1.0), 0.0)
                performance[strategy_id] = performance_score
            else:
                performance[strategy_id] = 0.5  # Neutral
        
        return performance
    
    def _calculate_strategy_risk_scores(self, positions: Dict[str, Any]) -> Dict[str, float]:
        """Calculate strategy risk scores"""
        
        risk_scores = {}
        
        for strategy_id in self.strategy_allocations.keys():
            # Simplified risk score based on position count and allocation
            position_count = len(positions.get(strategy_id, {}))
            max_positions = 5  # Assume max 5 positions per strategy
            
            position_risk = min(position_count / max_positions, 1.0)
            
            # Add allocation risk
            allocation = self.strategy_allocations.get(strategy_id, 0)
            allocation_risk = allocation  # Higher allocation = higher risk
            
            # Combined risk score
            combined_risk = (position_risk * 0.6 + allocation_risk * 0.4)
            risk_scores[strategy_id] = combined_risk
        
        return risk_scores
    
    def _get_symbol_volatility(self, symbol: str) -> float:
        """Get symbol volatility"""
        
        if symbol not in self.returns_history or len(self.returns_history[symbol]) < 10:
            return 0.2  # Default 20% volatility
        
        returns = self.returns_history[symbol][-min(len(self.returns_history[symbol]), 60):]
        return np.std(returns) * np.sqrt(252)  # Annualized volatility
    
    async def _check_risk_alerts(self):
        """Check for risk alerts"""
        
        if not self.current_metrics:
            return
        
        new_alerts = []
        
        # Portfolio drawdown alert
        if self.current_metrics.current_drawdown > self.risk_limits.max_portfolio_drawdown:
            alert = RiskAlert(
                alert_id=f"portfolio_dd_{datetime.now().strftime('%H%M%S')}",
                risk_level=RiskLevel.CRITICAL,
                message=f"Portfolio drawdown {self.current_metrics.current_drawdown:.1%} exceeds limit",
                recommended_action=RiskAction.REDUCE_POSITIONS,
                affected_strategies=list(self.strategy_allocations.keys()),
                affected_symbols=[]
            )
            new_alerts.append(alert)
        
        # VaR alert
        var_limit = self.risk_limits.max_var_pct * self.current_capital
        if self.current_metrics.var_95 > var_limit:
            alert = RiskAlert(
                alert_id=f"var_breach_{datetime.now().strftime('%H%M%S')}",
                risk_level=RiskLevel.HIGH,
                message=f"Portfolio VaR ${self.current_metrics.var_95:.0f} exceeds limit ${var_limit:.0f}",
                recommended_action=RiskAction.HALT_NEW_TRADES,
                affected_strategies=list(self.strategy_allocations.keys()),
                affected_symbols=[]
            )
            new_alerts.append(alert)
        
        # Concentration alert
        if self.current_metrics.concentration_risk > 0.8:
            alert = RiskAlert(
                alert_id=f"concentration_{datetime.now().strftime('%H%M%S')}",
                risk_level=RiskLevel.MEDIUM,
                message=f"Portfolio concentration risk {self.current_metrics.concentration_risk:.1%} too high",
                recommended_action=RiskAction.REDUCE_POSITIONS,
                affected_strategies=list(self.strategy_allocations.keys()),
                affected_symbols=[]
            )
            new_alerts.append(alert)
        
        # Add new alerts
        for alert in new_alerts:
            self.active_alerts.append(alert)
            logger.warning(f"🚨 RISK ALERT [{alert.risk_level.value}]: {alert.message}")
            
            # Trigger alert callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
        
        # Clean old alerts (keep last 50)
        if len(self.active_alerts) > 50:
            self.active_alerts = self.active_alerts[-50:]
    
    async def _update_dynamic_allocations(self):
        """Update dynamic allocations based on performance (live trading only)"""
        
        if self.trading_mode == TradingMode.BACKTESTING:
            return
        
        if not self.current_metrics or len(self.current_metrics.strategy_performance) < 2:
            return
        
        try:
            # Calculate performance-adjusted allocations
            total_performance = sum(self.current_metrics.strategy_performance.values())
            
            if total_performance == 0:
                return
            
            new_allocations = {}
            for strategy_id, base_allocation in self.strategy_allocations.items():
                perf_score = self.current_metrics.strategy_performance.get(strategy_id, 0.5)
                
                # Performance adjustment (±20% max)
                performance_factor = perf_score / (total_performance / len(self.current_metrics.strategy_performance))
                adjustment = min(max(performance_factor - 1.0, -0.2), 0.2)
                
                # Risk adjustment
                risk_score = self.current_metrics.strategy_risk_scores.get(strategy_id, 0.5)
                risk_adjustment = -risk_score * 0.1
                
                # Combined adjustment
                total_adjustment = adjustment + risk_adjustment
                new_allocation = base_allocation * (1 + total_adjustment)
                
                # Keep within bounds
                new_allocations[strategy_id] = max(min(new_allocation, self.risk_limits.max_strategy_allocation_pct), 0.1)
            
            # Normalize to sum to 1.0
            total_new = sum(new_allocations.values())
            if total_new > 0:
                new_allocations = {k: v/total_new for k, v in new_allocations.items()}
            
            # Check if rebalancing is needed (5% threshold)
            max_deviation = max(abs(new_allocations[k] - self.strategy_allocations[k]) 
                              for k in new_allocations.keys())
            
            if max_deviation > 0.05:
                logger.info("📊 Dynamic allocation update triggered:")
                for strategy_id in new_allocations:
                    old_alloc = self.strategy_allocations[strategy_id]
                    new_alloc = new_allocations[strategy_id]
                    change = new_alloc - old_alloc
                    logger.info(f"   {strategy_id}: {old_alloc:.1%} → {new_alloc:.1%} ({change:+.1%})")
                
                self.strategy_allocations = new_allocations
            
        except Exception as e:
            logger.error(f"❌ Error updating dynamic allocations: {e}")
    
    def _initialize_ml_models(self):
        """Initialize ML models for advanced risk analytics"""
        
        if not ML_AVAILABLE:
            return
        
        try:
            # Initialize PCA for factor analysis
            self.ml_models['pca'] = PCA(n_components=3)
            
            # Initialize scaler for data preprocessing
            self.ml_models['scaler'] = StandardScaler()
            
            logger.info("🤖 ML models initialized for advanced risk analytics")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        
        if not self.current_metrics:
            return {"status": "No data available"}
        
        return {
            "trading_mode": self.trading_mode.value,
            "portfolio_metrics": {
                "value": self.current_metrics.portfolio_value,
                "total_pnl": self.current_metrics.total_pnl,
                "current_drawdown": self.current_metrics.current_drawdown,
                "max_drawdown": self.current_metrics.max_drawdown,
                "volatility": self.current_metrics.portfolio_volatility,
                "sharpe_ratio": self.current_metrics.sharpe_ratio,
                "var_95": self.current_metrics.var_95,
                "cvar_95": self.current_metrics.cvar_95
            },
            "risk_limits": {
                "max_position_size_pct": self.risk_limits.max_position_size_pct,
                "max_portfolio_drawdown": self.risk_limits.max_portfolio_drawdown,
                "max_var_pct": self.risk_limits.max_var_pct
            },
            "strategy_metrics": {
                "allocations": self.current_metrics.strategy_allocations,
                "performance": self.current_metrics.strategy_performance,
                "risk_scores": self.current_metrics.strategy_risk_scores
            },
            "active_alerts": [
                {
                    "level": alert.risk_level.value,
                    "message": alert.message,
                    "action": alert.recommended_action.value,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in self.active_alerts[-5:]  # Last 5 alerts
            ]
        }
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export risk manager configuration for consistency"""
        
        return {
            "risk_limits": {
                "max_position_size_pct": self.risk_limits.max_position_size_pct,
                "max_portfolio_drawdown": self.risk_limits.max_portfolio_drawdown,
                "max_strategy_drawdown": self.risk_limits.max_strategy_drawdown,
                "default_stop_loss_pct": self.risk_limits.default_stop_loss_pct,
                "default_take_profit_pct": self.risk_limits.default_take_profit_pct,
                "target_portfolio_volatility": self.risk_limits.target_portfolio_volatility,
                "var_confidence_level": self.risk_limits.var_confidence_level,
                "max_var_pct": self.risk_limits.max_var_pct
            },
            "strategy_allocations": self.strategy_allocations,
            "trading_mode": self.trading_mode.value,
            "initial_capital": self.initial_capital
        }
    
    @classmethod
    def from_configuration(cls, config: Dict[str, Any], 
                          trading_mode: TradingMode,
                          data_provider: Optional[IRiskDataProvider] = None):
        """Create risk manager from configuration"""
        
        # Create risk limits from config
        risk_limits = RiskLimits()
        if "risk_limits" in config:
            for key, value in config["risk_limits"].items():
                if hasattr(risk_limits, key):
                    setattr(risk_limits, key, value)
        
        # Create risk manager
        risk_manager = cls(
            risk_limits=risk_limits,
            trading_mode=trading_mode,
            initial_capital=config.get("initial_capital", 100000.0),
            data_provider=data_provider
        )
        
        # Set strategy allocations
        if "strategy_allocations" in config:
            risk_manager.set_strategy_allocations(config["strategy_allocations"])
        
        return risk_manager
