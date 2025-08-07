"""
Core Risk Management System
==========================

Professional risk management system consolidating all risk functionality.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk levels for monitoring and alerting"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OrderType(Enum):
    """Order types for risk management"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"

@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size: float = 0.1
    max_sector_exposure: float = 0.3
    max_portfolio_risk: float = 0.02
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    trailing_stop_pct: float = 0.03
    max_drawdown: float = 0.15
    daily_loss_limit: float = 0.05
    max_volatility: float = 0.25
    var_confidence: float = 0.95

@dataclass
class PositionRisk:
    """Position-level risk metrics"""
    symbol: str
    position_size: float
    current_price: float
    avg_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    risk_level: RiskLevel
    alerts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics"""
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    current_drawdown: float
    max_drawdown: float
    risk_level: RiskLevel
    position_risks: Dict[str, PositionRisk] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RiskOrder:
    """Risk management order"""
    symbol: str
    quantity: int
    order_type: OrderType
    price: float
    trailing: bool = False
    triggered: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None

@dataclass
class PositionSize:
    """Position sizing result"""
    symbol: str
    position_size: float
    sizing_method: str
    confidence: float
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.risk_callbacks = []
        self.execution_callbacks = []
        self.position_risks = {}
        self.portfolio_risk = None
        self.stop_loss_orders = {}
        self.take_profit_orders = {}
        self.trailing_stop_orders = {}
        self.portfolio_value = 100000.0
        self.risk_free_rate = 0.02
        self.peak_value = 0.0
        self.current_drawdown = 0.0
        
        logger.info("Initialized comprehensive RiskManager")
    
    def add_risk_callback(self, callback: Callable):
        """Add callback for risk events"""
        self.risk_callbacks.append(callback)
        logger.info(f"Added risk callback: {callback.__name__}")
    
    def add_execution_callback(self, callback: Callable):
        """Add callback for order execution events"""
        self.execution_callbacks.append(callback)
        logger.info(f"Added execution callback: {callback.__name__}")
    
    def calculate_position_risk(self, symbol: str, position_size: float, 
                              current_price: float, avg_price: float) -> PositionRisk:
        """Calculate position risk metrics"""
        unrealized_pnl = (current_price - avg_price) * position_size
        unrealized_pnl_pct = (current_price - avg_price) / avg_price if avg_price > 0 else 0.0
        
        risk_level = self._determine_risk_level(unrealized_pnl_pct, position_size)
        alerts = self._generate_position_alerts(symbol, position_size, unrealized_pnl_pct)
        
        position_risk = PositionRisk(
            symbol=symbol,
            position_size=position_size,
            current_price=current_price,
            avg_price=avg_price,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            risk_level=risk_level,
            alerts=alerts
        )
        
        self.position_risks[symbol] = position_risk
        
        if alerts:
            for callback in self.risk_callbacks:
                try:
                    callback(symbol, position_risk)
                except Exception as e:
                    logger.error(f"Risk callback error: {e}")
        
        return position_risk
    
    def calculate_portfolio_risk(self, positions: Dict[str, Dict[str, Any]]) -> PortfolioRisk:
        """Calculate portfolio risk metrics"""
        position_risks = {}
        total_value = 0.0
        total_pnl = 0.0
        
        for symbol, position_data in positions.items():
            position_risk = self.calculate_position_risk(
                symbol=symbol,
                position_size=position_data.get('size', 0.0),
                current_price=position_data.get('current_price', 0.0),
                avg_price=position_data.get('avg_price', 0.0)
            )
            position_risks[symbol] = position_risk
            
            position_value = position_risk.position_size * position_risk.current_price
            total_value += position_value
            total_pnl += position_risk.unrealized_pnl
        
        total_pnl_pct = total_pnl / total_value if total_value > 0 else 0.0
        
        if total_value > self.peak_value:
            self.peak_value = total_value
        
        current_drawdown = (self.peak_value - total_value) / self.peak_value if self.peak_value > 0 else 0.0
        self.current_drawdown = max(self.current_drawdown, current_drawdown)
        
        risk_level = self._determine_portfolio_risk_level(total_pnl_pct, current_drawdown)
        alerts = self._generate_portfolio_alerts(total_pnl_pct, current_drawdown)
        
        portfolio_risk = PortfolioRisk(
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            current_drawdown=current_drawdown,
            max_drawdown=self.current_drawdown,
            risk_level=risk_level,
            position_risks=position_risks,
            alerts=alerts
        )
        
        self.portfolio_risk = portfolio_risk
        return portfolio_risk
    
    def create_stop_loss(self, symbol: str, quantity: int, avg_price: float,
                        stop_loss_pct: Optional[float] = None) -> RiskOrder:
        """Create stop-loss order"""
        stop_pct = stop_loss_pct or self.risk_limits.stop_loss_pct
        stop_price = avg_price * (1 - stop_pct)
        
        stop_order = RiskOrder(
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.STOP_LOSS,
            price=stop_price
        )
        
        self.stop_loss_orders[symbol] = stop_order
        logger.info(f"Created stop-loss for {symbol}: {quantity} @ ${stop_price:.2f}")
        return stop_order
    
    def create_take_profit(self, symbol: str, quantity: int, avg_price: float,
                          take_profit_pct: Optional[float] = None) -> RiskOrder:
        """Create take-profit order"""
        profit_pct = take_profit_pct or self.risk_limits.take_profit_pct
        target_price = avg_price * (1 + profit_pct)
        
        profit_order = RiskOrder(
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.TAKE_PROFIT,
            price=target_price
        )
        
        self.take_profit_orders[symbol] = profit_order
        logger.info(f"Created take-profit for {symbol}: {quantity} @ ${target_price:.2f}")
        return profit_order
    
    def create_trailing_stop(
        self,
        symbol: str,
        quantity: int,
        current_price: float,
        trailing_pct: Optional[float] = None
    ) -> RiskOrder:
        """Create trailing stop order"""
        
        trail_pct = trailing_pct or self.risk_limits.trailing_stop_pct
        stop_price = current_price * (1 - trail_pct)
        
        trailing_order = RiskOrder(
            symbol=symbol,
            quantity=quantity,
            order_type=OrderType.TRAILING_STOP,
            price=stop_price,
            trailing=True
        )
        
        self.trailing_stop_orders[symbol] = trailing_order
        
        logger.info(f"Created trailing stop for {symbol}: {quantity} @ ${stop_price:.2f} ({trail_pct:.1%})")
        return trailing_order
    
    def update_prices(self, market_data: Dict[str, float]):
        """Update prices and check for order triggers"""
        
        for symbol, current_price in market_data.items():
            # Check stop-loss orders
            if symbol in self.stop_loss_orders:
                order = self.stop_loss_orders[symbol]
                if current_price <= order.price and not order.triggered:
                    self._execute_order("STOP_LOSS", symbol, order, current_price)
            
            # Check take-profit orders
            if symbol in self.take_profit_orders:
                order = self.take_profit_orders[symbol]
                if current_price >= order.price and not order.triggered:
                    self._execute_order("TAKE_PROFIT", symbol, order, current_price)
            
            # Check trailing stop orders
            if symbol in self.trailing_stop_orders:
                order = self.trailing_stop_orders[symbol]
                if current_price <= order.price and not order.triggered:
                    self._execute_order("TRAILING_STOP", symbol, order, current_price)
                elif current_price > order.price:
                    # Update trailing stop price
                    trail_pct = self.risk_limits.trailing_stop_pct
                    new_stop_price = current_price * (1 - trail_pct)
                    if new_stop_price > order.price:
                        order.price = new_stop_price
                        logger.debug(f"Updated trailing stop for {symbol}: ${new_stop_price:.2f}")
    
    def calculate_position_size(self, symbol: str, signal_strength: float,
                              method: str = "signal_strength") -> PositionSize:
        """Calculate position size using specified method"""
        if method == "signal_strength":
            position_size = self._signal_strength_sizing(signal_strength)
        else:
            position_size = self._signal_strength_sizing(signal_strength)
        
        position_size = max(0.0, min(position_size, self.risk_limits.max_position_size))
        
        return PositionSize(
            symbol=symbol,
            position_size=position_size,
            sizing_method=method,
            confidence=abs(signal_strength),
            risk_metrics={'signal_strength': signal_strength}
        )
    
    def _signal_strength_sizing(self, signal_strength: float, base_position_size: float = 0.05) -> float:
        """Calculate position size based on signal strength"""
        normalized_signal = min(abs(signal_strength), 1.0)
        position_size = base_position_size * normalized_signal
        return max(0.0, min(position_size, self.risk_limits.max_position_size))
    
    def _determine_risk_level(self, pnl_pct: float, position_size: float) -> RiskLevel:
        """Determine risk level for position"""
        if pnl_pct <= -self.risk_limits.stop_loss_pct or position_size > self.risk_limits.max_position_size:
            return RiskLevel.HIGH
        elif pnl_pct < 0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _determine_portfolio_risk_level(self, pnl_pct: float, drawdown: float) -> RiskLevel:
        """Determine risk level for portfolio"""
        if (pnl_pct <= -self.risk_limits.daily_loss_limit or 
            drawdown > self.risk_limits.max_drawdown):
            return RiskLevel.CRITICAL
        elif pnl_pct < 0 or drawdown > self.risk_limits.max_drawdown * 0.5:
            return RiskLevel.HIGH
        elif pnl_pct < 0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_position_alerts(self, symbol: str, position_size: float, pnl_pct: float) -> List[str]:
        """Generate alerts for position"""
        alerts = []
        
        if pnl_pct <= -self.risk_limits.stop_loss_pct:
            alerts.append(f"Stop-loss triggered: {pnl_pct:.2%}")
        
        if position_size > self.risk_limits.max_position_size:
            alerts.append(f"Position size exceeds limit: {position_size:.2%}")
        
        return alerts
    
    def _generate_portfolio_alerts(self, pnl_pct: float, drawdown: float) -> List[str]:
        """Generate alerts for portfolio"""
        alerts = []
        
        if pnl_pct <= -self.risk_limits.daily_loss_limit:
            alerts.append(f"Daily loss limit exceeded: {pnl_pct:.2%}")
        
        if drawdown > self.risk_limits.max_drawdown:
            alerts.append(f"Maximum drawdown exceeded: {drawdown:.2%}")
        
        return alerts
    
    def should_stop_trading(self) -> bool:
        """Determine if trading should be stopped due to risk"""
        if self.portfolio_risk is None:
            return False
        
        return (
            self.portfolio_risk.risk_level == RiskLevel.CRITICAL or
            self.portfolio_risk.current_drawdown > self.risk_limits.max_drawdown or
            self.portfolio_risk.total_pnl_pct <= -self.risk_limits.daily_loss_limit
        )
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get risk summary"""
        return {
            'position_risks': {symbol: risk.__dict__ for symbol, risk in self.position_risks.items()},
            'portfolio_risk': self.portfolio_risk.__dict__ if self.portfolio_risk else None,
            'active_orders': {
                'stop_loss': len(self.stop_loss_orders),
                'take_profit': len(self.take_profit_orders),
                'trailing_stop': len(self.trailing_stop_orders)
            }
        }
    
    def shutdown(self):
        """Shutdown risk manager"""
        logger.info("Shutting down RiskManager") 