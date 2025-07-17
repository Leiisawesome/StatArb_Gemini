"""
Risk management utilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Production-grade risk management for trading strategies
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk manager with configuration
        
        Args:
            config: Configuration dictionary with risk parameters
        """
        risk_config = config.get('risk', {})
        
        self.max_position_size = risk_config.get('max_position_size', 0.45)  # Max 45% per position
        self.cash_reserve = risk_config.get('cash_reserve', 0.1)  # Keep 10% cash
        self.max_leverage = risk_config.get('max_leverage', 1.0)  # No leverage by default
        self.stop_loss = risk_config.get('stop_loss', None)  # Stop loss percentage
        self.max_drawdown_limit = risk_config.get('max_drawdown_limit', None)  # Portfolio stop
        
        logger.debug(f"RiskManager initialized with max_position_size={self.max_position_size}")
    
    def calculate_position_sizes(self, 
                               signals: Dict[str, str], 
                               current_prices: Dict[str, float],
                               available_cash: float) -> Dict[str, float]:
        """
        Calculate position sizes for given signals with risk controls
        
        Args:
            signals: Dictionary of trading signals {symbol: 'LONG'/'SHORT'}
            current_prices: Current prices for symbols
            available_cash: Available cash for trading
        
        Returns:
            Dictionary of position sizes {symbol: dollar_amount}
        """
        if not signals or available_cash <= 0:
            return {}
        
        # Apply cash reserve
        usable_cash = available_cash * (1 - self.cash_reserve)
        
        # Calculate equal weight allocation
        num_positions = len(signals)
        base_allocation = usable_cash / num_positions
        
        # Apply maximum position size limit
        max_position_value = available_cash * self.max_position_size
        target_position_size = min(base_allocation, max_position_value)
        
        # Validate position sizes
        position_sizes = {}
        total_allocated = 0
        
        for symbol, signal in signals.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                
                # Check minimum position size (avoid tiny positions)
                if target_position_size < price * 10:  # Minimum 10 shares
                    logger.warning(f"Position size too small for {symbol}: ${target_position_size:.2f}")
                    continue
                
                # Apply position size
                position_sizes[symbol] = target_position_size
                total_allocated += target_position_size
                
                logger.debug(f"Allocated ${target_position_size:.2f} to {symbol} {signal}")
        
        # Validate total allocation doesn't exceed available cash
        if total_allocated > usable_cash:
            # Scale down proportionally
            scale_factor = usable_cash / total_allocated
            position_sizes = {symbol: size * scale_factor for symbol, size in position_sizes.items()}
            logger.warning(f"Scaled down positions by {scale_factor:.3f} to fit available cash")
        
        return position_sizes
    
    def validate_signals(self, signals: Dict[str, str], 
                       current_positions: Dict[str, int], 
                       current_cash: float, 
                       portfolio_value: float, 
                       current_prices: Dict[str, float]) -> Dict[str, str]:
        """
        Validate trading signals against risk constraints
        
        Args:
            signals: Raw trading signals from strategy
            current_positions: Current position holdings
            current_cash: Available cash
            portfolio_value: Total portfolio value
            current_prices: Current market prices
            
        Returns:
            Validated signals that meet risk constraints
        """
        validated_signals = signals.copy()
        
        # Basic validation - ensure we have prices for all signals
        validated_signals = {
            symbol: signal for symbol, signal in validated_signals.items()
            if symbol in current_prices and current_prices[symbol] > 0
        }
        
        logger.debug(f"Validated {len(validated_signals)} signals from {len(signals)} original signals")
        return validated_signals
    
    def check_portfolio_risk(self, 
                           portfolio_value: float,
                           peak_value: float,
                           positions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Check overall portfolio risk metrics
        
        Args:
            portfolio_value: Current portfolio value
            peak_value: Historical peak value
            positions: Current positions
        
        Returns:
            Risk status and recommendations
        """
        risk_status = {
            'status': 'OK',
            'warnings': [],
            'actions': []
        }
        
        # Check drawdown limit
        if self.max_drawdown_limit and peak_value > 0:
            current_drawdown = (portfolio_value / peak_value) - 1
            if current_drawdown < -self.max_drawdown_limit:
                risk_status['status'] = 'CRITICAL'
                risk_status['warnings'].append(f"Portfolio drawdown {current_drawdown:.2%} exceeds limit {-self.max_drawdown_limit:.2%}")
                risk_status['actions'].append("Consider reducing position sizes or stopping trading")
        
        # Check position concentration
        if positions:
            total_exposure = sum(abs(pos.get('shares', 0) * pos.get('entry_price', 0)) for pos in positions.values())
            if total_exposure > portfolio_value * self.max_leverage:
                risk_status['status'] = 'WARNING'
                risk_status['warnings'].append(f"Total exposure exceeds leverage limit")
                risk_status['actions'].append("Reduce position sizes")
        
        return risk_status
    
    def validate_trade(self, 
                      symbol: str,
                      side: str,
                      quantity: float,
                      price: float,
                      current_portfolio_value: float) -> bool:
        """
        Validate individual trade before execution
        
        Args:
            symbol: Trading symbol
            side: 'LONG' or 'SHORT'
            quantity: Number of shares
            price: Execution price
            current_portfolio_value: Current portfolio value
        
        Returns:
            True if trade is acceptable, False otherwise
        """
        trade_value = quantity * price
        
        # Check position size limit
        if trade_value > current_portfolio_value * self.max_position_size:
            logger.warning(f"Trade rejected: Position size {trade_value:.2f} exceeds limit")
            return False
        
        # Check minimum trade size
        if trade_value < 1000:  # Minimum $1000 trade
            logger.warning(f"Trade rejected: Position size {trade_value:.2f} too small")
            return False
        
        # Check price sanity
        if price <= 0:
            logger.error(f"Trade rejected: Invalid price {price}")
            return False
        
        return True
    
    def calculate_stop_loss_price(self, 
                                entry_price: float, 
                                side: str) -> Optional[float]:
        """
        Calculate stop loss price if configured
        
        Args:
            entry_price: Position entry price
            side: 'LONG' or 'SHORT'
        
        Returns:
            Stop loss price or None if not configured
        """
        if not self.stop_loss:
            return None
        
        if side == 'LONG':
            return entry_price * (1 - self.stop_loss)
        else:  # SHORT
            return entry_price * (1 + self.stop_loss)
    
    def emergency_liquidation_check(self, 
                                  portfolio_history: pd.DataFrame) -> bool:
        """
        Check if emergency liquidation is needed
        
        Args:
            portfolio_history: Historical portfolio values
        
        Returns:
            True if emergency liquidation recommended
        """
        if len(portfolio_history) < 5:  # Need some history
            return False
        
        # Check for rapid portfolio decline
        recent_values = portfolio_history['total_value'].tail(5)
        decline_rate = (recent_values.iloc[-1] / recent_values.iloc[0]) - 1
        
        if decline_rate < -0.15:  # 15% decline in 5 periods
            logger.critical(f"Emergency liquidation triggered: {decline_rate:.2%} decline")
            return True
        
        return False
