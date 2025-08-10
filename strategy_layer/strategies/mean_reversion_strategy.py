"""
Mean Reversion Strategy Implementation

Concrete mean reversion trading strategy implementation using building blocks.

Author: Pro Quant Desk Trader
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyResult, StrategyExecutionResult, StrategyError
from strategy_layer.blocks import SignalGenerator, PositionSizer, RiskManager, EntryExitLogic


class MeanReversionStrategyDefinition(StrategyDefinition):
    """Mean reversion trading strategy implementation"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_building_blocks()
    
    def _setup_building_blocks(self):
        """Setup building blocks for mean reversion strategy"""
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
            
            self.logger.info("Mean reversion strategy building blocks setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up building blocks: {e}")
            raise StrategyError(f"Failed to setup mean reversion strategy: {e}")
    
    def calculate_moving_averages(self, market_data: pd.DataFrame, short_period: int = 10, long_period: int = 30) -> Tuple[pd.Series, pd.Series]:
        """Calculate short and long moving averages"""
        try:
            short_ma = market_data['close'].rolling(window=short_period).mean()
            long_ma = market_data['close'].rolling(window=long_period).mean()
            
            return short_ma, long_ma
            
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float)
    
    def calculate_bollinger_bands(self, market_data: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        try:
            sma = market_data['close'].rolling(window=period).mean()
            rolling_std = market_data['close'].rolling(window=period).std()
            
            upper_band = sma + (rolling_std * std_dev)
            lower_band = sma - (rolling_std * std_dev)
            
            return upper_band, sma, lower_band
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    def calculate_rsi(self, market_data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        try:
            close_prices = market_data['close']
            delta = close_prices.diff()
            
            gains = delta.where(delta > 0, 0)
            losses = -delta.where(delta < 0, 0)
            
            avg_gains = gains.rolling(window=period).mean()
            avg_losses = losses.rolling(window=period).mean()
            
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(dtype=float)
    
    def calculate_mean_reversion_signals(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate mean reversion specific signals"""
        try:
            signals = {}
            
            # Calculate moving averages
            short_ma, long_ma = self.calculate_moving_averages(market_data)
            
            # Calculate Bollinger Bands
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(market_data)
            
            # Calculate RSI
            rsi = self.calculate_rsi(market_data)
            
            # Generate mean reversion signals
            if not short_ma.empty and not long_ma.empty:
                current_price = market_data['close'].iloc[-1]
                current_short_ma = short_ma.iloc[-1]
                current_long_ma = long_ma.iloc[-1]
                
                # Moving average mean reversion signal
                ma_deviation = (current_price - current_long_ma) / current_long_ma
                ma_signal = -ma_deviation  # Revert to mean
                signals['MA_MeanReversion'] = np.clip(ma_signal, -1.0, 1.0)
            
            # Bollinger Bands mean reversion signal
            if not upper_band.empty and not lower_band.empty:
                current_upper = upper_band.iloc[-1]
                current_lower = lower_band.iloc[-1]
                current_middle = middle_band.iloc[-1]
                
                if current_upper != current_lower:
                    # Calculate %B (position within bands)
                    percent_b = (current_price - current_lower) / (current_upper - current_lower)
                    
                    # Mean reversion signal based on %B
                    if percent_b > 1.0:  # Above upper band
                        bb_signal = -1.0  # Short signal
                    elif percent_b < 0.0:  # Below lower band
                        bb_signal = 1.0  # Long signal
                    else:
                        # Normalize signal between -1 and 1
                        bb_signal = (0.5 - percent_b) * 2
                    
                    signals['BB_MeanReversion'] = bb_signal
            
            # RSI mean reversion signal
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                
                if current_rsi > 70:  # Overbought
                    rsi_signal = -1.0  # Short signal
                elif current_rsi < 30:  # Oversold
                    rsi_signal = 1.0  # Long signal
                else:
                    # Normalize signal between -1 and 1
                    rsi_signal = (50 - current_rsi) / 50
                
                signals['RSI_MeanReversion'] = rsi_signal
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion signals: {e}")
            return {}
    
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate trading signals using signal generator"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # Get base signals from signal generator
            base_signals = self.signal_generator.generate_signals(market_data)
            
            # Get mean reversion specific signals
            mean_reversion_signals = self.calculate_mean_reversion_signals(market_data)
            
            # Combine all signals
            all_signals = {**base_signals, **mean_reversion_signals}
            
            return all_signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return {}
    
    def generate_mean_reversion_signals(self, market_data: pd.DataFrame) -> Dict[str, float]:
        """Generate mean reversion trading signals"""
        try:
            # Get base signals from signal generator
            base_signals = self.signal_generator.generate_signals(market_data)
            
            # Get mean reversion specific signals
            mean_reversion_signals = self.calculate_mean_reversion_signals(market_data)
            
            # Combine all signals
            all_signals = {**base_signals, **mean_reversion_signals}
            
            return all_signals
            
        except Exception as e:
            self.logger.error(f"Error generating mean reversion signals: {e}")
            return {}
    
    def generate_combined_mean_reversion_signal(self, market_data: pd.DataFrame) -> float:
        """Generate combined mean reversion signal"""
        try:
            signals = self.generate_mean_reversion_signals(market_data)
            
            if not signals:
                return 0.0
            
            # Combine signals using signal generator
            combined_signal = self.signal_generator.combine_signals(signals)
            
            return combined_signal
            
        except Exception as e:
            self.logger.error(f"Error generating combined mean reversion signal: {e}")
            return 0.0
    
    def generate_combined_signal(self, market_data: pd.DataFrame) -> float:
        """Generate combined trading signal"""
        try:
            return self.generate_combined_mean_reversion_signal(market_data)
        except Exception as e:
            self.logger.error(f"Error generating combined signal: {e}")
            return 0.0
    
    def calculate_position_sizes(self, signals: Dict[str, float], market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate position sizes based on signals and market data"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # Combine signals into a single signal
            combined_signal = sum(signals.values()) / len(signals) if signals else 0.0
            
            # Calculate position size (simplified - in practice would be more sophisticated)
            position_size = abs(combined_signal) * 0.05  # 5% of portfolio per unit signal
            
            return {"default": position_size}
        except Exception as e:
            self.logger.error(f"Error calculating position sizes: {e}")
            return {}
    
    def calculate_mean_reversion_position_size(self, signal: float, market_data: pd.DataFrame, 
                                             portfolio_value: float, current_positions: Dict[str, float]) -> float:
        """Calculate position size for mean reversion strategy"""
        try:
            # For mean reversion, we might want to adjust position sizing based on deviation from mean
            base_position_size = self.position_sizer.calculate_position_size(
                signal, market_data, portfolio_value, current_positions
            )
            
            # Calculate deviation from mean for position size adjustment
            short_ma, long_ma = self.calculate_moving_averages(market_data)
            
            if not long_ma.empty:
                current_price = market_data['close'].iloc[-1]
                current_ma = long_ma.iloc[-1]
                
                if current_ma > 0:
                    deviation = abs(current_price - current_ma) / current_ma
                    
                    # Adjust position size based on deviation (larger deviation = larger position)
                    deviation_factor = min(deviation * 2, 1.0)  # Cap at 1.0
                    adjusted_position_size = base_position_size * (1 + deviation_factor)
                    
                    return adjusted_position_size
            
            return base_position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion position size: {e}")
            return 0.0
    
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
    
    def should_enter_mean_reversion_position(self, symbol: str, signal: float, market_data: pd.DataFrame, 
                                           portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should enter mean reversion position"""
        try:
            # Check basic entry conditions
            should_enter, reason = self.entry_exit_logic.should_enter_position(
                symbol, signal, market_data, portfolio_data
            )
            
            if should_enter:
                # Additional mean reversion specific checks
                # Check if price is significantly deviated from mean
                short_ma, long_ma = self.calculate_moving_averages(market_data)
                
                if not long_ma.empty:
                    current_price = market_data['close'].iloc[-1]
                    current_ma = long_ma.iloc[-1]
                    
                    if current_ma > 0:
                        deviation = abs(current_price - current_ma) / current_ma
                        
                        # Only enter if deviation is significant (e.g., > 2%)
                        if deviation < 0.02:
                            return False, "Deviation from mean too small for mean reversion"
            
            return should_enter, reason
            
        except Exception as e:
            self.logger.error(f"Error checking mean reversion entry conditions: {e}")
            return False, f"Error: {e}"
    
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
    
    def should_exit_mean_reversion_position(self, symbol: str, position: float, signal: float, 
                                          market_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should exit mean reversion position"""
        try:
            # Check basic exit conditions
            should_exit, reason = self.entry_exit_logic.should_exit_position(
                symbol, position, signal, market_data, portfolio_data
            )
            
            if not should_exit:
                # Additional mean reversion specific exit checks
                # Check if price has reverted to mean
                short_ma, long_ma = self.calculate_moving_averages(market_data)
                
                if not long_ma.empty:
                    current_price = market_data['close'].iloc[-1]
                    current_ma = long_ma.iloc[-1]
                    
                    if current_ma > 0:
                        deviation = abs(current_price - current_ma) / current_ma
                        
                        # Exit if price has reverted close to mean (e.g., < 0.5%)
                        if deviation < 0.005:
                            return True, "Price reverted to mean"
            
            return should_exit, reason
            
        except Exception as e:
            self.logger.error(f"Error checking mean reversion exit conditions: {e}")
            return False, f"Error: {e}"
    
    def execute_strategy(self, symbol: str, market_data: pd.DataFrame, 
                        portfolio_value: float, current_positions: Dict[str, float],
                        portfolio_data: Dict[str, Any]) -> StrategyExecutionResult:
        """Execute the mean reversion strategy"""
        return self.execute_mean_reversion_strategy(symbol, market_data, portfolio_value, current_positions, portfolio_data)
    
    def execute_mean_reversion_strategy(self, symbol: str, market_data: pd.DataFrame, 
                                      portfolio_value: float, current_positions: Dict[str, float],
                                      portfolio_data: Dict[str, Any]) -> StrategyExecutionResult:
        """Execute the mean reversion strategy"""
        try:
            self.logger.info(f"Executing mean reversion strategy for {symbol}")
            
            # Step 1: Generate mean reversion signal
            signal = self.generate_combined_mean_reversion_signal(market_data)
            self.logger.info(f"Generated mean reversion signal: {signal:.3f}")
            
            # Step 2: Check entry conditions
            should_enter, entry_reason = self.should_enter_mean_reversion_position(
                symbol, signal, market_data, portfolio_data
            )
            
            if should_enter:
                # Step 3: Calculate position size
                position_size = self.calculate_mean_reversion_position_size(
                    signal, market_data, portfolio_value, current_positions
                )
                
                if position_size != 0:
                    # Step 4: Calculate entry price
                    entry_price = market_data['close'].iloc[-1]
                    
                    # Step 5: Calculate stop loss and take profit
                    stop_loss = self.risk_manager.calculate_stop_loss(entry_price, position_size, market_data)
                    take_profit = self.risk_manager.calculate_take_profit(entry_price, position_size, market_data)
                    
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
                            "strategy_type": "mean_reversion",
                            "entry_reason": entry_reason,
                            "signal": signal
                        }
                    )
                    
                    self.logger.info(f"Mean reversion strategy executed: {result.action} {result.position_size:.3f} at {result.entry_price:.2f}")
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
                            "strategy_type": "mean_reversion",
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
                        "strategy_type": "mean_reversion",
                        "reason": entry_reason,
                        "signal": signal
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error executing mean reversion strategy: {e}")
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
                    "strategy_type": "mean_reversion",
                    "error": str(e)
                }
            )
    
    def evaluate_mean_reversion_exit(self, symbol: str, position: float, entry_price: float, 
                                   current_price: float, market_data: pd.DataFrame,
                                   portfolio_data: Dict[str, Any]) -> StrategyResult:
        """Evaluate exit conditions for existing mean reversion position"""
        try:
            # Generate current signal
            signal = self.generate_combined_mean_reversion_signal(market_data)
            
            # Check exit conditions
            should_exit, exit_reason = self.should_exit_mean_reversion_position(
                symbol, position, signal, market_data, portfolio_data
            )
            
            # Check risk limits
            risk_exit, risk_reason = self.risk_manager.should_exit_position(
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
                        "strategy_type": "mean_reversion",
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
                        "strategy_type": "mean_reversion",
                        "reason": "Position maintained",
                        "signal": signal
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Error evaluating mean reversion exit: {e}")
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
                    "strategy_type": "mean_reversion",
                    "error": str(e)
                }
            )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        try:
            return {
                "strategy_id": self.config.strategy_id,
                "strategy_name": self.config.name,
                "strategy_type": "mean_reversion",
                "version": self.config.version,
                "description": self.config.description,
                "signal_generator": "SignalGenerator",
                "position_sizer": self.position_sizer.get_method(),
                "risk_manager": "RiskManager",
                "entry_exit_logic": "EntryExitLogic",
                "parameters": self.config.parameters
            }
        except Exception as e:
            self.logger.error(f"Error getting strategy info: {e}")
            return {}
    
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
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        try:
            # Update the config
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Re-setup building blocks with new config
            self._setup_building_blocks()
            
            self.logger.info("Mean reversion strategy configuration updated")
            
        except Exception as e:
            self.logger.error(f"Error updating strategy config: {e}")
            raise StrategyError(f"Failed to update mean reversion strategy config: {e}")
