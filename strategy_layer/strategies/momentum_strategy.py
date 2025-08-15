"""
Momentum Strategy Implementation

Concrete momentum trading strategy implementation using building blocks.

Author: Pro Quant Desk Trader
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyResult, StrategyExecutionResult, StrategyError
from strategy_layer.blocks import SignalGenerator, PositionSizer, RiskManager, EntryExitLogic


class MomentumStrategyDefinition(StrategyDefinition):
    """Momentum trading strategy implementation"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_building_blocks()
    
    def _setup_building_blocks(self):
        """Setup building blocks for momentum strategy"""
        try:
            # Setup signal generator
            signal_config = self.config.signal_generation
            self.signal_generator = SignalGenerator(signal_config)
            
            # Setup position sizer
            position_config = self.config.risk_management.get('position_sizing', {})
            self.position_sizer = PositionSizer(position_config)
            
            # Setup risk manager
            risk_config = self.config.risk_management
            self.risk_manager = RiskManager(risk_config)
            
            # Setup entry/exit logic
            logic_config = self.config.entry_exit_logic
            self.entry_exit_logic = EntryExitLogic(logic_config)
            
            self.logger.info("Momentum strategy building blocks setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up building blocks: {e}")
            raise StrategyError(f"Failed to setup momentum strategy: {e}")
    
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate momentum signals including both entry and exit signals"""
        try:
            # Extract data from the market_data structure
            if 'market_data' in market_data:
                data = market_data['market_data']
            elif 'data' in market_data:
                data = market_data['data']
            else:
                data = market_data
            
            # Ensure we have a DataFrame
            if not isinstance(data, pd.DataFrame):
                self.logger.warning("Market data is not a DataFrame")
                return {}
            
            if len(data) < self.config.parameters.get('lookback_period', 5):
                self.logger.warning(f"Insufficient data for momentum calculation: {len(data)} < {self.config.parameters.get('lookback_period', 5)}")
                return {}
            
            # Calculate momentum using the configured lookback period
            lookback = self.config.parameters.get('lookback_period', 5)
            
            # Get recent price data
            if 'close' in data.columns:
                recent_prices = data['close'].tail(lookback + 1)
                if len(recent_prices) >= 2:
                    # Calculate momentum as percentage change
                    momentum = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
                    
                    # Calculate confidence based on price consistency
                    price_changes = recent_prices.pct_change().dropna()
                    if len(price_changes) > 0:
                        consistency = 1.0 - price_changes.std()  # Higher consistency = higher confidence
                        confidence = max(0.1, min(1.0, consistency))
                    else:
                        confidence = 0.5
                    
                    # 🎯 PROFESSIONAL EXIT SIGNAL GENERATION
                    signals = {
                        'momentum': momentum,
                        'confidence': confidence,
                        'lookback_period': lookback,
                        'data_points': len(recent_prices)
                    }
                    
                    # Add exit signals based on momentum reversal (VERY AGGRESSIVE)
                    exit_threshold = self.config.parameters.get('exit_threshold', -0.0005)  # Even more sensitive
                    if momentum < exit_threshold:
                        signals['exit_signal'] = abs(momentum)  # Exit signal strength
                        signals['exit_reason'] = 'momentum_reversal'
                        self.logger.info(f"🔴 EXIT SIGNAL: Momentum reversal {momentum:.4f} < {exit_threshold}")
                    
                    # Add profit/loss exit signals if we have position info
                    current_price = recent_prices.iloc[-1]
                    prev_price = recent_prices.iloc[-2] if len(recent_prices) > 1 else current_price
                    
                    # Quick profit taking signal (VERY AGGRESSIVE)
                    profit_threshold = self.config.risk_management.get('take_profit', 0.01)  # Just 1%!
                    quick_profit = (current_price - prev_price) / prev_price
                    if quick_profit >= profit_threshold:
                        signals['profit_exit_signal'] = quick_profit
                        signals['exit_reason'] = 'take_profit'
                        self.logger.info(f"🔴 PROFIT EXIT: Quick gain {quick_profit:.4f} >= {profit_threshold}")
                    
                    # Stop loss signal (VERY AGGRESSIVE)  
                    stop_loss_threshold = self.config.risk_management.get('stop_loss', 0.005)  # Just 0.5%!
                    if quick_profit <= -stop_loss_threshold:
                        signals['stop_loss_signal'] = abs(quick_profit)
                        signals['exit_reason'] = 'stop_loss'
                        self.logger.info(f"🔴 STOP LOSS: Loss {quick_profit:.4f} <= -{stop_loss_threshold}")
                    
                    # 🎯 PROFESSIONAL DEBUG: Always generate some exit signal for testing
                    if abs(momentum) > 0.0001:  # Almost any momentum should trigger some analysis
                        self.logger.info(f"📊 MOMENTUM ANALYSIS: {momentum:.4f}, quick_profit: {quick_profit:.4f}")
                    
                    self.logger.debug(f"Momentum signal: {momentum:.4f}, confidence: {confidence:.2f}")
                    
                    return signals
            
            self.logger.warning("No 'close' column found in market data")
            return {}
            
        except Exception as e:
            self.logger.error(f"Error generating momentum signals: {e}")
            return {}
    
    def generate_combined_signal(self, market_data: pd.DataFrame) -> float:
        """Generate combined trading signal"""
        try:
            return self.signal_generator.generate_combined_signal(market_data)
        except Exception as e:
            self.logger.error(f"Error generating combined signal: {e}")
            return 0.0
    
    def calculate_position_size(self, signal: float, market_data: pd.DataFrame, 
                              portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate position size using position sizer"""
        try:
            return self.position_sizer.calculate_position_size(
                signal, market_data, portfolio_value, current_positions
            )
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def calculate_position_sizes(self, signals: Dict[str, float], market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate position sizes based on signals and market data"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # PROFESSIONAL FIX: Only use actual trading signals, not metadata
            # Extract only the momentum signal value, ignore confidence/metadata
            momentum_signal = signals.get('momentum', 0.0)
            
            # Calculate position size based on momentum strength
            # Use configured position_size from strategy config as base
            base_position_size = self.config.parameters.get('position_size', 0.05)  # Default 5%
            
            # Scale by momentum strength (cap at 2x for safety)
            signal_multiplier = min(abs(momentum_signal) * 100, 2.0)  # Convert to percentage scale
            position_size = base_position_size * signal_multiplier
            
            # Cap at maximum position size
            max_position = self.config.parameters.get('max_position_size', 0.5)  # Default 50%
            position_size = min(position_size, max_position)
            
            self.logger.info(f"💡 POSITION CALC: momentum={momentum_signal:.4f}, base={base_position_size:.1%}, multiplier={signal_multiplier:.2f}, final={position_size:.1%}")
            
            return {"default": position_size}
        except Exception as e:
            self.logger.error(f"Error calculating position sizes: {e}")
            return {}
    
    def should_enter_position(self, symbol: str, signal: float, market_data: Dict[str, Any]) -> bool:
        """Determine if should enter a position"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # Use entry/exit logic to determine if should enter
            should_enter, _ = self.entry_exit_logic.should_enter_position(
                symbol, signal, market_data, {}
            )
            return should_enter
        except Exception as e:
            self.logger.error(f"Error checking entry conditions: {e}")
            return False
    
    def should_exit_position(self, symbol: str, position: float, market_data: Dict[str, Any]) -> bool:
        """Determine if should exit a position"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # Use entry/exit logic to determine if should exit
            should_exit, _ = self.entry_exit_logic.should_exit_position(
                symbol, position, 0.0, market_data, {}
            )
            return should_exit
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return False
    
    def validate_risk(self, positions: Dict[str, float], market_data: Dict[str, Any]) -> bool:
        """Validate risk parameters for positions"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # Basic risk validation - check if total position size is within limits
            total_position_size = sum(abs(pos) for pos in positions.values())
            max_allowed = self.config.risk_management.get('max_portfolio_allocation', 0.2)
            
            if total_position_size > max_allowed:
                self.logger.warning(f"Total position size {total_position_size:.3f} exceeds limit {max_allowed}")
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Error validating risk: {e}")
            return False
    
    def check_risk_limits(self, symbol: str, position: float, entry_price: float, 
                         current_price: float, market_data: pd.DataFrame, 
                         portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check risk limits using risk manager"""
        try:
            return self.risk_manager.should_exit_position(
                symbol, position, entry_price, current_price, market_data, portfolio_data
            )
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
            return False, f"Error: {e}"
    
    def calculate_stop_loss(self, entry_price: float, position: float, 
                          market_data: pd.DataFrame) -> float:
        """Calculate stop loss using risk manager"""
        try:
            return self.risk_manager.calculate_stop_loss(entry_price, position, market_data)
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return 0.0
    
    def calculate_take_profit(self, entry_price: float, position: float, 
                            market_data: pd.DataFrame) -> float:
        """Calculate take profit using risk manager"""
        try:
            return self.risk_manager.calculate_take_profit(entry_price, position, market_data)
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return 0.0
    
    def execute_strategy(self, symbol: str, market_data: pd.DataFrame, 
                        portfolio_value: float, current_positions: Dict[str, float],
                        portfolio_data: Dict[str, Any]) -> StrategyExecutionResult:
        """Execute the momentum strategy"""
        try:
            self.logger.info(f"Executing momentum strategy for {symbol}")
            
            # Step 1: Generate signal
            signal = self.generate_combined_signal(market_data)
            self.logger.info(f"Generated signal: {signal:.3f}")
            
            # Step 2: Check entry conditions
            should_enter, entry_reason = self.should_enter_position(
                symbol, signal, market_data, portfolio_data
            )
            
            if should_enter:
                # Step 3: Calculate position size
                position_size = self.calculate_position_size(
                    signal, market_data, portfolio_value, current_positions
                )
                
                if position_size != 0:
                    # Step 4: Calculate entry price
                    entry_price = market_data['close'].iloc[-1]
                    
                    # Step 5: Calculate stop loss and take profit
                    stop_loss = self.calculate_stop_loss(entry_price, position_size, market_data)
                    take_profit = self.calculate_take_profit(entry_price, position_size, market_data)
                    
                    # Step 6: Create strategy result
                    result = StrategyExecutionResult(
                        strategy_id=self.config.strategy_id,
                        symbol=symbol,
                        action="BUY" if position_size > 0 else "SELL",
                        position_size=abs(position_size),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        signal_strength=abs(signal),
                        confidence=min(abs(signal), 1.0),
                        timestamp=datetime.now(),
                        metadata={
                            "strategy_type": "momentum",
                            "entry_reason": entry_reason,
                            "signal": signal
                        }
                    )
                    
                    self.logger.info(f"Momentum strategy executed: {result.action} {result.position_size:.3f} at {result.entry_price:.2f}")
                    return result
                else:
                    self.logger.info("Position size is zero, no action taken")
                    return StrategyExecutionResult(
                        strategy_id=self.config.strategy_id,
                        symbol=symbol,
                        action="HOLD",
                        position_size=0.0,
                        entry_price=0.0,
                        stop_loss=0.0,
                        take_profit=0.0,
                        signal_strength=abs(signal),
                        confidence=0.0,
                        timestamp=datetime.now(),
                        metadata={
                            "strategy_type": "momentum",
                            "reason": "Position size is zero",
                            "signal": signal
                        }
                    )
            else:
                self.logger.info(f"Entry conditions not met: {entry_reason}")
                return StrategyExecutionResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol,
                    action="HOLD",
                    position_size=0.0,
                    entry_price=0.0,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=0.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "momentum",
                        "reason": entry_reason,
                        "signal": signal
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error executing momentum strategy: {e}")
            return StrategyExecutionResult(
                strategy_id=self.config.strategy_id,
                symbol=symbol,
                action="ERROR",
                position_size=0.0,
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                signal_strength=0.0,
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={
                    "strategy_type": "momentum",
                    "error": str(e)
                }
            )
    
    def evaluate_exit(self, symbol: str, position: float, entry_price: float, 
                     current_price: float, market_data: pd.DataFrame,
                     portfolio_data: Dict[str, Any]) -> StrategyResult:
        """Evaluate exit conditions for existing position"""
        try:
            # Generate current signal
            signal = self.generate_combined_signal(market_data)
            
            # Check exit conditions
            should_exit, exit_reason = self.should_exit_position(
                symbol, position, signal, market_data, portfolio_data
            )
            
            # Check risk limits
            risk_exit, risk_reason = self.check_risk_limits(
                symbol, position, entry_price, current_price, market_data, portfolio_data
            )
            
            if should_exit or risk_exit:
                action = "SELL" if position > 0 else "BUY"
                reason = exit_reason if should_exit else risk_reason
                
                return StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol,
                    action=action,
                    position_size=abs(position),
                    entry_price=entry_price,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=1.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "momentum",
                        "exit_reason": reason,
                        "signal": signal
                    }
                )
            else:
                return StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol,
                    action="HOLD",
                    position_size=abs(position),
                    entry_price=entry_price,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=0.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "momentum",
                        "reason": "Position maintained",
                        "signal": signal
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error evaluating exit: {e}")
            return StrategyResult(
                strategy_id=self.config.strategy_id,
                symbol=symbol,
                action="ERROR",
                position_size=abs(position),
                entry_price=entry_price,
                stop_loss=0.0,
                take_profit=0.0,
                signal_strength=0.0,
                confidence=0.0,
                timestamp=datetime.now(),
                metadata={
                    "strategy_type": "momentum",
                    "error": str(e)
                }
            )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        try:
            return {
                "strategy_id": self.config.strategy_id,
                "strategy_name": self.config.name,
                "strategy_type": "momentum",
                "version": self.config.version,
                "description": self.config.description,
                "signal_generator": self.signal_generator.get_method() if hasattr(self.signal_generator, 'get_method') else "SignalGenerator",
                "position_sizer": self.position_sizer.get_method(),
                "risk_manager": "RiskManager",
                "entry_exit_logic": "EntryExitLogic",
                "parameters": self.config.parameters
            }
        except Exception as e:
            self.logger.error(f"Error getting strategy info: {e}")
            return {}
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        try:
            # Update the config
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Re-setup building blocks with new config
            self._setup_building_blocks()
            
            self.logger.info("Momentum strategy configuration updated")
            
        except Exception as e:
            self.logger.error(f"Error updating strategy config: {e}")
            raise StrategyError(f"Failed to update momentum strategy config: {e}")
