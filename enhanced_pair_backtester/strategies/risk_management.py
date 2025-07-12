"""
Risk Management System

Professional risk management for pairs trading with:
- Stop-loss and take-profit controls
- Position limits and concentration risk
- Drawdown controls and circuit breakers
- Portfolio-level risk monitoring
- Dynamic risk adjustment based on market conditions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging

# Import execution components
try:
    from ..execution.execution_engine import ExecutionEngine, TradeRequest, ExecutionResult
    from ..execution.order_management import Position
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from execution.execution_engine import ExecutionEngine, TradeRequest, ExecutionResult
    from execution.order_management import Position


class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class RiskAction(Enum):
    """Risk management actions"""
    ALLOW = "allow"
    REDUCE = "reduce"
    BLOCK = "block"
    LIQUIDATE = "liquidate"


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    # Position limits
    max_position_size: float = 0.1  # 10% of portfolio per position
    max_pair_concentration: float = 0.2  # 20% of portfolio per pair
    max_sector_concentration: float = 0.3  # 30% of portfolio per sector
    
    # Stop-loss limits
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.15  # 15% take profit
    trailing_stop_pct: float = 0.03  # 3% trailing stop
    
    # Drawdown controls
    max_daily_drawdown: float = 0.02  # 2% daily drawdown limit
    max_total_drawdown: float = 0.10  # 10% total drawdown limit
    
    # Volatility controls
    max_portfolio_volatility: float = 0.15  # 15% annualized volatility
    volatility_lookback_days: int = 30
    
    # Liquidity controls
    max_volume_participation: float = 0.10  # 10% of daily volume
    min_liquidity_threshold: float = 1000000  # $1M minimum daily volume


@dataclass
class RiskMetrics:
    """Current risk metrics"""
    current_drawdown: float = 0.0
    daily_drawdown: float = 0.0
    portfolio_volatility: float = 0.0
    concentration_risk: float = 0.0
    liquidity_risk: float = 0.0
    var_95: float = 0.0  # 95% Value at Risk
    
    # Position-level metrics
    positions_at_risk: int = 0
    stop_loss_violations: int = 0
    
    # Risk level assessment
    overall_risk_level: RiskLevel = RiskLevel.LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'current_drawdown': self.current_drawdown,
            'daily_drawdown': self.daily_drawdown,
            'portfolio_volatility': self.portfolio_volatility,
            'concentration_risk': self.concentration_risk,
            'liquidity_risk': self.liquidity_risk,
            'var_95': self.var_95,
            'positions_at_risk': self.positions_at_risk,
            'stop_loss_violations': self.stop_loss_violations,
            'overall_risk_level': self.overall_risk_level.value
        }


@dataclass
class DrawdownControl:
    """Drawdown control state"""
    peak_value: float = 0.0
    current_value: float = 0.0
    max_drawdown: float = 0.0
    drawdown_start_date: Optional[datetime] = None
    recovery_target: float = 0.0
    
    # Circuit breaker state
    circuit_breaker_active: bool = False
    circuit_breaker_triggered_at: Optional[datetime] = None
    
    def update(self, current_value: float):
        """Update drawdown metrics"""
        self.current_value = current_value
        
        # Update peak
        if current_value > self.peak_value:
            self.peak_value = current_value
            self.drawdown_start_date = None
            self.recovery_target = 0.0
        
        # Calculate drawdown
        if self.peak_value > 0:
            drawdown = (self.peak_value - current_value) / self.peak_value
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                if self.drawdown_start_date is None:
                    self.drawdown_start_date = datetime.now()
                    self.recovery_target = self.peak_value * 0.95  # 95% recovery target
    
    @property
    def current_drawdown(self) -> float:
        """Current drawdown percentage"""
        if self.peak_value <= 0:
            return 0.0
        return (self.peak_value - self.current_value) / self.peak_value


class RiskManager:
    """
    Comprehensive risk management system for pairs trading
    
    Features:
    - Real-time risk monitoring
    - Position-level stop-loss/take-profit
    - Portfolio-level drawdown controls
    - Dynamic risk adjustment
    - Circuit breaker mechanisms
    """
    
    def __init__(self, 
                 risk_limits: RiskLimits,
                 initial_capital: float = 1000000,
                 enable_circuit_breaker: bool = True):
        """
        Initialize risk manager
        
        Args:
            risk_limits: Risk limits configuration
            initial_capital: Initial portfolio capital
            enable_circuit_breaker: Whether to enable circuit breaker
        """
        self.risk_limits = risk_limits
        self.initial_capital = initial_capital
        self.enable_circuit_breaker = enable_circuit_breaker
        
        # Risk tracking
        self.drawdown_control = DrawdownControl()
        self.risk_metrics = RiskMetrics()
        
        # Position tracking
        self.position_stops: Dict[str, Dict[str, float]] = {}  # symbol -> {stop_loss, take_profit, trailing_stop}
        self.position_entry_prices: Dict[str, float] = {}
        self.position_high_water_marks: Dict[str, float] = {}
        
        # Historical data for risk calculations
        self.portfolio_values: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        
        # Circuit breaker state
        self.trading_halted = False
        self.halt_reason = ""
        self.halt_start_time: Optional[datetime] = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def evaluate_trade_risk(self, 
                           trade_request: TradeRequest,
                           current_positions: Dict[str, Position],
                           current_prices: Dict[str, float],
                           portfolio_value: float) -> Tuple[RiskAction, str]:
        """
        Evaluate risk for a proposed trade
        
        Args:
            trade_request: Proposed trade
            current_positions: Current positions
            current_prices: Current market prices
            portfolio_value: Current portfolio value
            
        Returns:
            Tuple of (risk_action, reason)
        """
        # Check if trading is halted
        if self.trading_halted:
            return RiskAction.BLOCK, f"Trading halted: {self.halt_reason}"
        
        # Check position size limits
        position_risk = self._check_position_limits(
            trade_request, current_positions, current_prices, portfolio_value
        )
        if position_risk[0] != RiskAction.ALLOW:
            return position_risk
        
        # Check concentration limits
        concentration_risk = self._check_concentration_limits(
            trade_request, current_positions, current_prices, portfolio_value
        )
        if concentration_risk[0] != RiskAction.ALLOW:
            return concentration_risk
        
        # Check drawdown limits
        drawdown_risk = self._check_drawdown_limits(portfolio_value)
        if drawdown_risk[0] != RiskAction.ALLOW:
            return drawdown_risk
        
        # Check volatility limits
        volatility_risk = self._check_volatility_limits(current_positions, current_prices)
        if volatility_risk[0] != RiskAction.ALLOW:
            return volatility_risk
        
        return RiskAction.ALLOW, "Trade approved"
    
    def update_position_stops(self, 
                            symbol: str,
                            current_price: float,
                            position: Position):
        """
        Update stop-loss and take-profit levels for a position
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            position: Current position
        """
        if position.quantity == 0:
            # Remove stops for closed positions
            if symbol in self.position_stops:
                del self.position_stops[symbol]
            return
        
        # Initialize stops if new position
        if symbol not in self.position_stops:
            self.position_stops[symbol] = {}
            self.position_entry_prices[symbol] = position.average_price
            self.position_high_water_marks[symbol] = current_price
        
        entry_price = self.position_entry_prices[symbol]
        is_long = position.quantity > 0
        
        # Calculate stop-loss
        if is_long:
            stop_loss = entry_price * (1 - self.risk_limits.stop_loss_pct)
            take_profit = entry_price * (1 + self.risk_limits.take_profit_pct)
        else:
            stop_loss = entry_price * (1 + self.risk_limits.stop_loss_pct)
            take_profit = entry_price * (1 - self.risk_limits.take_profit_pct)
        
        # Update trailing stop
        if is_long:
            if current_price > self.position_high_water_marks[symbol]:
                self.position_high_water_marks[symbol] = current_price
            trailing_stop = self.position_high_water_marks[symbol] * (1 - self.risk_limits.trailing_stop_pct)
            # Use the higher of fixed stop-loss and trailing stop
            stop_loss = max(stop_loss, trailing_stop)
        else:
            if current_price < self.position_high_water_marks[symbol]:
                self.position_high_water_marks[symbol] = current_price
            trailing_stop = self.position_high_water_marks[symbol] * (1 + self.risk_limits.trailing_stop_pct)
            # Use the lower of fixed stop-loss and trailing stop
            stop_loss = min(stop_loss, trailing_stop)
        
        self.position_stops[symbol] = {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'trailing_stop': self.position_high_water_marks[symbol]
        }
    
    def check_stop_loss_triggers(self, 
                               current_positions: Dict[str, Position],
                               current_prices: Dict[str, float]) -> List[TradeRequest]:
        """
        Check for stop-loss triggers and generate exit orders
        
        Args:
            current_positions: Current positions
            current_prices: Current market prices
            
        Returns:
            List of stop-loss trade requests
        """
        exit_orders = []
        
        for symbol, position in current_positions.items():
            if position.quantity == 0 or symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            self.update_position_stops(symbol, current_price, position)
            
            if symbol not in self.position_stops:
                continue
            
            stops = self.position_stops[symbol]
            is_long = position.quantity > 0
            
            # Check stop-loss trigger
            stop_triggered = False
            trigger_reason = ""
            
            if is_long and current_price <= stops['stop_loss']:
                stop_triggered = True
                trigger_reason = f"Long stop-loss triggered: {current_price:.4f} <= {stops['stop_loss']:.4f}"
            elif not is_long and current_price >= stops['stop_loss']:
                stop_triggered = True
                trigger_reason = f"Short stop-loss triggered: {current_price:.4f} >= {stops['stop_loss']:.4f}"
            
            # Check take-profit trigger
            elif is_long and current_price >= stops['take_profit']:
                stop_triggered = True
                trigger_reason = f"Long take-profit triggered: {current_price:.4f} >= {stops['take_profit']:.4f}"
            elif not is_long and current_price <= stops['take_profit']:
                stop_triggered = True
                trigger_reason = f"Short take-profit triggered: {current_price:.4f} <= {stops['take_profit']:.4f}"
            
            if stop_triggered:
                # Create exit order
                exit_order = TradeRequest(
                    symbol=symbol,
                    side="sell" if is_long else "buy",
                    quantity=abs(position.quantity),
                    order_type="market",
                    strategy_id="risk_management",
                    notes=trigger_reason
                )
                exit_orders.append(exit_order)
                
                self.logger.info(f"Stop triggered for {symbol}: {trigger_reason}")
                self.risk_metrics.stop_loss_violations += 1
        
        return exit_orders
    
    def update_portfolio_risk(self, 
                            portfolio_value: float,
                            current_positions: Dict[str, Position],
                            current_prices: Dict[str, float]):
        """
        Update portfolio-level risk metrics
        
        Args:
            portfolio_value: Current portfolio value
            current_positions: Current positions
            current_prices: Current market prices
        """
        # Update drawdown control
        self.drawdown_control.update(portfolio_value)
        
        # Store portfolio value history
        self.portfolio_values.append((datetime.now(), portfolio_value))
        
        # Calculate daily returns
        if len(self.portfolio_values) > 1:
            prev_value = self.portfolio_values[-2][1]
            daily_return = (portfolio_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
            
            # Keep only recent returns for volatility calculation
            if len(self.daily_returns) > self.risk_limits.volatility_lookback_days:
                self.daily_returns = self.daily_returns[-self.risk_limits.volatility_lookback_days:]
        
        # Update risk metrics
        self.risk_metrics.current_drawdown = self.drawdown_control.current_drawdown
        self.risk_metrics.daily_drawdown = self._calculate_daily_drawdown()
        self.risk_metrics.portfolio_volatility = self._calculate_portfolio_volatility()
        self.risk_metrics.concentration_risk = self._calculate_concentration_risk(
            current_positions, current_prices, portfolio_value
        )
        self.risk_metrics.var_95 = self._calculate_var_95()
        
        # Count positions at risk
        self.risk_metrics.positions_at_risk = self._count_positions_at_risk(
            current_positions, current_prices
        )
        
        # Assess overall risk level
        self.risk_metrics.overall_risk_level = self._assess_overall_risk_level()
        
        # Check circuit breaker conditions
        if self.enable_circuit_breaker:
            self._check_circuit_breaker(portfolio_value)
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive risk summary
        
        Returns:
            Dictionary with risk metrics and status
        """
        return {
            'risk_metrics': self.risk_metrics.to_dict(),
            'drawdown_control': {
                'peak_value': self.drawdown_control.peak_value,
                'current_value': self.drawdown_control.current_value,
                'current_drawdown': self.drawdown_control.current_drawdown,
                'max_drawdown': self.drawdown_control.max_drawdown,
                'circuit_breaker_active': self.drawdown_control.circuit_breaker_active
            },
            'position_stops': {
                symbol: {
                    'stop_loss': stops['stop_loss'],
                    'take_profit': stops['take_profit'],
                    'trailing_stop': stops['trailing_stop']
                }
                for symbol, stops in self.position_stops.items()
            },
            'trading_status': {
                'trading_halted': self.trading_halted,
                'halt_reason': self.halt_reason,
                'halt_start_time': self.halt_start_time.isoformat() if self.halt_start_time else None
            }
        }
    
    def _check_position_limits(self, 
                              trade_request: TradeRequest,
                              current_positions: Dict[str, Position],
                              current_prices: Dict[str, float],
                              portfolio_value: float) -> Tuple[RiskAction, str]:
        """Check position size limits"""
        if trade_request.symbol not in current_prices:
            return RiskAction.BLOCK, f"Price not available for {trade_request.symbol}"
        
        current_price = current_prices[trade_request.symbol]
        trade_value = trade_request.quantity * current_price
        
        # Get current position
        current_position = current_positions.get(trade_request.symbol)
        current_position_value = 0.0
        if current_position:
            current_position_value = abs(current_position.quantity * current_price)
        
        # Calculate new position value
        if trade_request.side == "buy":
            new_position_value = current_position_value + trade_value
        else:
            new_position_value = max(0, current_position_value - trade_value)
        
        # Check position size limit
        position_pct = new_position_value / portfolio_value
        if position_pct > self.risk_limits.max_position_size:
            return RiskAction.REDUCE, f"Position size limit exceeded: {position_pct:.2%} > {self.risk_limits.max_position_size:.2%}"
        
        return RiskAction.ALLOW, "Position size within limits"
    
    def _check_concentration_limits(self, 
                                   trade_request: TradeRequest,
                                   current_positions: Dict[str, Position],
                                   current_prices: Dict[str, float],
                                   portfolio_value: float) -> Tuple[RiskAction, str]:
        """Check concentration limits (simplified - assumes all positions are in same sector)"""
        total_position_value = 0.0
        
        for symbol, position in current_positions.items():
            if symbol in current_prices:
                position_value = abs(position.quantity * current_prices[symbol])
                total_position_value += position_value
        
        # Add proposed trade value
        if trade_request.symbol in current_prices:
            trade_value = trade_request.quantity * current_prices[trade_request.symbol]
            if trade_request.side == "buy":
                total_position_value += trade_value
        
        concentration_pct = total_position_value / portfolio_value
        if concentration_pct > self.risk_limits.max_sector_concentration:
            return RiskAction.REDUCE, f"Concentration limit exceeded: {concentration_pct:.2%} > {self.risk_limits.max_sector_concentration:.2%}"
        
        return RiskAction.ALLOW, "Concentration within limits"
    
    def _check_drawdown_limits(self, portfolio_value: float) -> Tuple[RiskAction, str]:
        """Check drawdown limits"""
        # Check daily drawdown
        if len(self.portfolio_values) > 0:
            start_of_day_value = self.portfolio_values[-1][1]  # Simplified - use last value
            daily_drawdown = (start_of_day_value - portfolio_value) / start_of_day_value
            
            if daily_drawdown > self.risk_limits.max_daily_drawdown:
                return RiskAction.BLOCK, f"Daily drawdown limit exceeded: {daily_drawdown:.2%} > {self.risk_limits.max_daily_drawdown:.2%}"
        
        # Check total drawdown
        current_drawdown = self.drawdown_control.current_drawdown
        if current_drawdown > self.risk_limits.max_total_drawdown:
            return RiskAction.BLOCK, f"Total drawdown limit exceeded: {current_drawdown:.2%} > {self.risk_limits.max_total_drawdown:.2%}"
        
        return RiskAction.ALLOW, "Drawdown within limits"
    
    def _check_volatility_limits(self, 
                                current_positions: Dict[str, Position],
                                current_prices: Dict[str, float]) -> Tuple[RiskAction, str]:
        """Check portfolio volatility limits"""
        if self.risk_metrics.portfolio_volatility > self.risk_limits.max_portfolio_volatility:
            return RiskAction.REDUCE, f"Portfolio volatility too high: {self.risk_metrics.portfolio_volatility:.2%} > {self.risk_limits.max_portfolio_volatility:.2%}"
        
        return RiskAction.ALLOW, "Volatility within limits"
    
    def _calculate_daily_drawdown(self) -> float:
        """Calculate daily drawdown"""
        if len(self.portfolio_values) < 2:
            return 0.0
        
        today_start = self.portfolio_values[-1][1]  # Simplified
        current_value = self.portfolio_values[-1][1]
        
        return (today_start - current_value) / today_start if today_start > 0 else 0.0
    
    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility"""
        if len(self.daily_returns) < 2:
            return 0.0
        
        return np.std(self.daily_returns) * np.sqrt(252)  # Annualized
    
    def _calculate_concentration_risk(self, 
                                    current_positions: Dict[str, Position],
                                    current_prices: Dict[str, float],
                                    portfolio_value: float) -> float:
        """Calculate concentration risk metric"""
        if portfolio_value <= 0:
            return 0.0
        
        position_weights = []
        for symbol, position in current_positions.items():
            if symbol in current_prices:
                position_value = abs(position.quantity * current_prices[symbol])
                weight = position_value / portfolio_value
                position_weights.append(weight)
        
        if not position_weights:
            return 0.0
        
        # Calculate Herfindahl index as concentration measure
        herfindahl_index = sum(w**2 for w in position_weights)
        return herfindahl_index
    
    def _calculate_var_95(self) -> float:
        """Calculate 95% Value at Risk"""
        if len(self.daily_returns) < 10:
            return 0.0
        
        return float(np.percentile(self.daily_returns, 5))  # 5th percentile for 95% VaR
    
    def _count_positions_at_risk(self, 
                                current_positions: Dict[str, Position],
                                current_prices: Dict[str, float]) -> int:
        """Count positions approaching stop-loss"""
        positions_at_risk = 0
        
        for symbol, position in current_positions.items():
            if position.quantity == 0 or symbol not in current_prices:
                continue
            
            if symbol not in self.position_stops:
                continue
            
            current_price = current_prices[symbol]
            stop_loss = self.position_stops[symbol]['stop_loss']
            is_long = position.quantity > 0
            
            # Check if within 20% of stop-loss
            if is_long:
                distance_to_stop = (current_price - stop_loss) / current_price
                if distance_to_stop < 0.2:  # Within 20% of stop
                    positions_at_risk += 1
            else:
                distance_to_stop = (stop_loss - current_price) / current_price
                if distance_to_stop < 0.2:  # Within 20% of stop
                    positions_at_risk += 1
        
        return positions_at_risk
    
    def _assess_overall_risk_level(self) -> RiskLevel:
        """Assess overall portfolio risk level"""
        risk_score = 0
        
        # Drawdown contribution
        if self.risk_metrics.current_drawdown > 0.05:
            risk_score += 3
        elif self.risk_metrics.current_drawdown > 0.03:
            risk_score += 2
        elif self.risk_metrics.current_drawdown > 0.01:
            risk_score += 1
        
        # Volatility contribution
        if self.risk_metrics.portfolio_volatility > 0.20:
            risk_score += 3
        elif self.risk_metrics.portfolio_volatility > 0.15:
            risk_score += 2
        elif self.risk_metrics.portfolio_volatility > 0.10:
            risk_score += 1
        
        # Concentration contribution
        if self.risk_metrics.concentration_risk > 0.5:
            risk_score += 2
        elif self.risk_metrics.concentration_risk > 0.3:
            risk_score += 1
        
        # Positions at risk contribution
        if self.risk_metrics.positions_at_risk > 2:
            risk_score += 2
        elif self.risk_metrics.positions_at_risk > 0:
            risk_score += 1
        
        # Classify risk level
        if risk_score >= 7:
            return RiskLevel.EXTREME
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _check_circuit_breaker(self, portfolio_value: float):
        """Check circuit breaker conditions"""
        # Check for extreme drawdown
        if self.drawdown_control.current_drawdown > self.risk_limits.max_total_drawdown * 0.8:
            self._trigger_circuit_breaker(f"Approaching maximum drawdown: {self.drawdown_control.current_drawdown:.2%}")
        
        # Check for extreme daily loss
        if len(self.portfolio_values) > 0:
            start_value = self.portfolio_values[0][1]
            daily_loss = (start_value - portfolio_value) / start_value
            if daily_loss > self.risk_limits.max_daily_drawdown * 1.5:
                self._trigger_circuit_breaker(f"Extreme daily loss: {daily_loss:.2%}")
        
        # Check for extreme volatility
        if self.risk_metrics.portfolio_volatility > self.risk_limits.max_portfolio_volatility * 1.5:
            self._trigger_circuit_breaker(f"Extreme volatility: {self.risk_metrics.portfolio_volatility:.2%}")
    
    def _trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker to halt trading"""
        if not self.trading_halted:
            self.trading_halted = True
            self.halt_reason = reason
            self.halt_start_time = datetime.now()
            self.drawdown_control.circuit_breaker_active = True
            self.drawdown_control.circuit_breaker_triggered_at = datetime.now()
            
            self.logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker (manual intervention)"""
        self.trading_halted = False
        self.halt_reason = ""
        self.halt_start_time = None
        self.drawdown_control.circuit_breaker_active = False
        
        self.logger.info("Circuit breaker reset - trading resumed") 