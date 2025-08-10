"""
Pair Trading Strategy Implementation

Concrete pair trading strategy implementation using building blocks.

Author: Pro Quant Desk Trader
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyResult, StrategyExecutionResult, StrategyError
from strategy_layer.blocks import SignalGenerator, PositionSizer, RiskManager, EntryExitLogic


class PairTradingStrategyDefinition(StrategyDefinition):
    """Pair trading strategy implementation"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_building_blocks()
    
    def _setup_building_blocks(self):
        """Setup building blocks for pair trading strategy"""
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
            
            self.logger.info("Pair trading strategy building blocks setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up building blocks: {e}")
            raise StrategyError(f"Failed to setup pair trading strategy: {e}")
    
    def prepare_pair_data(self, symbol1_data: pd.DataFrame, symbol2_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for pair trading analysis"""
        try:
            # Ensure both datasets have the same index
            common_index = symbol1_data.index.intersection(symbol2_data.index)
            
            if len(common_index) < 50:
                raise StrategyError("Insufficient common data for pair trading")
            
            # Create pair data with both price series
            pair_data = pd.DataFrame(index=common_index)
            pair_data['price1'] = symbol1_data.loc[common_index, 'close']
            pair_data['price2'] = symbol2_data.loc[common_index, 'close']
            
            # Add other required columns for building blocks
            pair_data['open'] = symbol1_data.loc[common_index, 'open']
            pair_data['high'] = symbol1_data.loc[common_index, 'high']
            pair_data['low'] = symbol1_data.loc[common_index, 'low']
            pair_data['close'] = symbol1_data.loc[common_index, 'close']
            pair_data['volume'] = symbol1_data.loc[common_index, 'volume']
            
            return pair_data
            
        except Exception as e:
            self.logger.error(f"Error preparing pair data: {e}")
            raise StrategyError(f"Failed to prepare pair data: {e}")
    
    def calculate_spread(self, pair_data: pd.DataFrame) -> pd.Series:
        """Calculate the spread between the two assets"""
        try:
            # Calculate the spread (difference between prices)
            spread = pair_data['price1'] - pair_data['price2']
            return spread
            
        except Exception as e:
            self.logger.error(f"Error calculating spread: {e}")
            return pd.Series(dtype=float)
    
    def calculate_zscore(self, spread: pd.Series, lookback_period: int = 20) -> pd.Series:
        """Calculate Z-score of the spread"""
        try:
            # Calculate rolling mean and standard deviation
            rolling_mean = spread.rolling(window=lookback_period).mean()
            rolling_std = spread.rolling(window=lookback_period).std()
            
            # Calculate Z-score
            zscore = (spread - rolling_mean) / rolling_std
            
            return zscore
            
        except Exception as e:
            self.logger.error(f"Error calculating Z-score: {e}")
            return pd.Series(dtype=float)
    
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate trading signals using signal generator"""
        try:
            # Convert dict to DataFrame if needed
            if isinstance(market_data, dict):
                market_data = pd.DataFrame(market_data)
            
            # For pair trading, we need to handle the case where market_data might be pair data
            if 'price1' in market_data.columns and 'price2' in market_data.columns:
                return self.generate_pair_signals(market_data)
            else:
                # Fallback to regular signal generation
                return self.signal_generator.generate_signals(market_data)
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return {}
    
    def generate_pair_signals(self, pair_data: pd.DataFrame) -> Dict[str, float]:
        """Generate trading signals for pair trading"""
        try:
            # Calculate spread
            spread = self.calculate_spread(pair_data)
            
            # Calculate Z-score
            zscore = self.calculate_zscore(spread)
            
            # Generate signals using signal generator
            signals = self.signal_generator.generate_signals(pair_data)
            
            # Add Z-score signal
            if not zscore.empty:
                current_zscore = zscore.iloc[-1]
                
                # Generate Z-score based signal
                if current_zscore > 2.0:  # Overvalued
                    zscore_signal = -1.0  # Short signal
                elif current_zscore < -2.0:  # Undervalued
                    zscore_signal = 1.0  # Long signal
                else:
                    # Normalize signal between -1 and 1
                    zscore_signal = -current_zscore / 2.0
                
                signals['ZScore'] = zscore_signal
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating pair signals: {e}")
            return {}
    
    def generate_combined_pair_signal(self, pair_data: pd.DataFrame) -> float:
        """Generate combined signal for pair trading"""
        try:
            signals = self.generate_pair_signals(pair_data)
            
            if not signals:
                return 0.0
            
            # Combine signals using signal generator
            combined_signal = self.signal_generator.combine_signals(signals)
            
            return combined_signal
            
        except Exception as e:
            self.logger.error(f"Error generating combined pair signal: {e}")
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
    
    def calculate_pair_position_sizes(self, signal: float, pair_data: pd.DataFrame, 
                                    portfolio_value: float, current_positions: Dict[str, float]) -> Tuple[float, float]:
        """Calculate position sizes for both assets in the pair"""
        try:
            # Calculate base position size
            base_position_size = self.position_sizer.calculate_position_size(
                signal, pair_data, portfolio_value, current_positions
            )
            
            # For pair trading, we take opposite positions in both assets
            # If signal is positive, we're long asset1 and short asset2
            # If signal is negative, we're short asset1 and long asset2
            
            if signal > 0:
                position1 = base_position_size  # Long asset1
                position2 = -base_position_size  # Short asset2
            else:
                position1 = -base_position_size  # Short asset1
                position2 = base_position_size  # Long asset2
            
            return position1, position2
            
        except Exception as e:
            self.logger.error(f"Error calculating pair position sizes: {e}")
            return 0.0, 0.0
    
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
    
    def should_enter_pair_position(self, symbol1: str, symbol2: str, signal: float, 
                                 pair_data: pd.DataFrame, portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should enter pair position"""
        try:
            # Check entry conditions for the primary symbol
            should_enter, reason = self.entry_exit_logic.should_enter_position(
                symbol1, signal, pair_data, portfolio_data
            )
            
            return should_enter, reason
            
        except Exception as e:
            self.logger.error(f"Error checking pair entry conditions: {e}")
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
    
    def should_exit_pair_position(self, symbol1: str, symbol2: str, position1: float, position2: float, 
                                signal: float, pair_data: pd.DataFrame, 
                                portfolio_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if should exit pair position"""
        try:
            # Check exit conditions for the primary symbol
            should_exit, reason = self.entry_exit_logic.should_exit_position(
                symbol1, position1, signal, pair_data, portfolio_data
            )
            
            return should_exit, reason
            
        except Exception as e:
            self.logger.error(f"Error checking pair exit conditions: {e}")
            return False, f"Error: {e}"
    
    def execute_pair_strategy(self, symbol1: str, symbol2: str, symbol1_data: pd.DataFrame, 
                            symbol2_data: pd.DataFrame, portfolio_value: float, 
                            current_positions: Dict[str, float], portfolio_data: Dict[str, Any]) -> List[StrategyExecutionResult]:
        """Execute the pair trading strategy"""
        try:
            self.logger.info(f"Executing pair trading strategy for {symbol1} and {symbol2}")
            
            # Step 1: Prepare pair data
            pair_data = self.prepare_pair_data(symbol1_data, symbol2_data)
            
            # Step 2: Generate signal
            signal = self.generate_combined_pair_signal(pair_data)
            self.logger.info(f"Generated pair signal: {signal:.3f}")
            
            # Step 3: Check entry conditions
            should_enter, entry_reason = self.should_enter_pair_position(
                symbol1, symbol2, signal, pair_data, portfolio_data
            )
            
            results = []
            
            if should_enter:
                # Step 4: Calculate position sizes
                position1, position2 = self.calculate_pair_position_sizes(
                    signal, pair_data, portfolio_value, current_positions
                )
                
                if position1 != 0 and position2 != 0:
                    # Step 5: Calculate entry prices
                    entry_price1 = symbol1_data['close'].iloc[-1]
                    entry_price2 = symbol2_data['close'].iloc[-1]
                    
                    # Step 6: Calculate stop loss and take profit
                    stop_loss1 = self.risk_manager.calculate_stop_loss(entry_price1, position1, symbol1_data)
                    take_profit1 = self.risk_manager.calculate_take_profit(entry_price1, position1, symbol1_data)
                    stop_loss2 = self.risk_manager.calculate_stop_loss(entry_price2, position2, symbol2_data)
                    take_profit2 = self.risk_manager.calculate_take_profit(entry_price2, position2, symbol2_data)
                    
                    # Step 7: Create strategy results for both assets
                    result1 = StrategyExecutionResult(
                        strategy_id=self.config.strategy_id,
                        symbol=symbol1,
                        action="BUY" if position1 > 0 else "SELL",
                        position_size=abs(position1),
                        entry_price=entry_price1,
                        stop_loss=stop_loss1,
                        take_profit=take_profit1,
                        signal_strength=abs(signal),
                        confidence=min(abs(signal), 1.0),
                        timestamp=datetime.now(),
                        metadata={
                            "strategy_type": "pair_trading",
                            "pair_symbol": symbol2,
                            "entry_reason": entry_reason,
                            "signal": signal
                        }
                    )
                    
                    result2 = StrategyExecutionResult(
                        strategy_id=self.config.strategy_id,
                        symbol=symbol2,
                        action="BUY" if position2 > 0 else "SELL",
                        position_size=abs(position2),
                        entry_price=entry_price2,
                        stop_loss=stop_loss2,
                        take_profit=take_profit2,
                        signal_strength=abs(signal),
                        confidence=min(abs(signal), 1.0),
                        timestamp=datetime.now(),
                        metadata={
                            "strategy_type": "pair_trading",
                            "pair_symbol": symbol1,
                            "entry_reason": entry_reason,
                            "signal": signal
                        }
                    )
                    
                    results = [result1, result2]
                    
                    self.logger.info(f"Pair trading executed: {result1.action} {result1.position_size:.3f} {symbol1}, {result2.action} {result2.position_size:.3f} {symbol2}")
                else:
                    self.logger.info("Position sizes are zero, no action taken")
                    results = [
                        StrategyExecutionResult(
                            strategy_id=self.config.strategy_id,
                            symbol=symbol1,
                            action="HOLD",
                            position_size=0.0,
                            entry_price=0.0,
                            stop_loss=0.0,
                            take_profit=0.0,
                            signal_strength=abs(signal),
                            confidence=0.0,
                            timestamp=datetime.now(),
                            metadata={
                                "strategy_type": "pair_trading",
                                "pair_symbol": symbol2,
                                "reason": "Position sizes are zero",
                                "signal": signal
                            }
                        )
                    ]
            else:
                self.logger.info(f"Entry conditions not met: {entry_reason}")
                results = [
                    StrategyExecutionResult(
                        strategy_id=self.config.strategy_id,
                        symbol=symbol1,
                        action="HOLD",
                        position_size=0.0,
                        entry_price=0.0,
                        stop_loss=0.0,
                        take_profit=0.0,
                        signal_strength=abs(signal),
                        confidence=0.0,
                        timestamp=datetime.now(),
                        metadata={
                            "strategy_type": "pair_trading",
                            "pair_symbol": symbol2,
                            "reason": entry_reason,
                            "signal": signal
                        }
                    )
                ]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error executing pair trading strategy: {e}")
            return [
                StrategyExecutionResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol1,
                    action="ERROR",
                    position_size=0.0,
                    entry_price=0.0,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=0.0,
                    confidence=0.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "pair_trading",
                        "pair_symbol": symbol2,
                        "error": str(e)
                    }
                )
            ]
    
    def evaluate_pair_exit(self, symbol1: str, symbol2: str, position1: float, position2: float,
                          entry_price1: float, entry_price2: float, current_price1: float, current_price2: float,
                          symbol1_data: pd.DataFrame, symbol2_data: pd.DataFrame,
                          portfolio_data: Dict[str, Any]) -> List[StrategyResult]:
        """Evaluate exit conditions for existing pair position"""
        try:
            # Prepare pair data
            pair_data = self.prepare_pair_data(symbol1_data, symbol2_data)
            
            # Generate current signal
            signal = self.generate_combined_pair_signal(pair_data)
            
            # Check exit conditions
            should_exit, exit_reason = self.should_exit_pair_position(
                symbol1, symbol2, position1, position2, signal, pair_data, portfolio_data
            )
            
            # Check risk limits for both positions
            risk_exit1, risk_reason1 = self.risk_manager.should_exit_position(
                symbol1, position1, entry_price1, current_price1, symbol1_data, portfolio_data
            )
            
            risk_exit2, risk_reason2 = self.risk_manager.should_exit_position(
                symbol2, position2, entry_price2, current_price2, symbol2_data, portfolio_data
            )
            
            results = []
            
            if should_exit or risk_exit1 or risk_exit2:
                # Exit both positions
                action1 = "SELL" if position1 > 0 else "BUY"
                action2 = "SELL" if position2 > 0 else "BUY"
                
                reason1 = exit_reason if should_exit else risk_reason1
                reason2 = exit_reason if should_exit else risk_reason2
                
                result1 = StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol1,
                    action=action1,
                    position_size=abs(position1),
                    entry_price=entry_price1,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=1.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "pair_trading",
                        "pair_symbol": symbol2,
                        "exit_reason": reason1,
                        "signal": signal
                    }
                )
                
                result2 = StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol2,
                    action=action2,
                    position_size=abs(position2),
                    entry_price=entry_price2,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=1.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "pair_trading",
                        "pair_symbol": symbol1,
                        "exit_reason": reason2,
                        "signal": signal
                    }
                )
                
                results = [result1, result2]
            else:
                # Maintain both positions
                result1 = StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol1,
                    action="HOLD",
                    position_size=abs(position1),
                    entry_price=entry_price1,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=abs(signal),
                    confidence=0.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "pair_trading",
                        "pair_symbol": symbol2,
                        "reason": "Position maintained",
                        "signal": signal
                    }
                )
                
                results = [result1]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error evaluating pair exit: {e}")
            return [
                StrategyResult(
                    strategy_id=self.config.strategy_id,
                    symbol=symbol1,
                    action="ERROR",
                    position_size=abs(position1),
                    entry_price=entry_price1,
                    stop_loss=0.0,
                    take_profit=0.0,
                    signal_strength=0.0,
                    confidence=0.0,
                    timestamp=datetime.now(),
                    metadata={
                        "strategy_type": "pair_trading",
                        "pair_symbol": symbol2,
                        "error": str(e)
                    }
                )
            ]
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        try:
            return {
                "strategy_id": self.config.strategy_id,
                "strategy_name": self.config.name,
                "strategy_type": "pair_trading",
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
            
            self.logger.info("Pair trading strategy configuration updated")
            
        except Exception as e:
            self.logger.error(f"Error updating strategy config: {e}")
            raise StrategyError(f"Failed to update pair trading strategy config: {e}")
