"""
Enhanced Breakout Strategy with ISystemComponent Integration
==========================================================

Professional breakout strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

Key Features:
- Pattern-based breakout detection
- Volume confirmation
- False breakout filtering
- Dynamic position sizing
- Professional risk management

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy, StrategyPerformanceMetrics
from ...strategy_engine import (
    StrategyConfig, StrategySignal, StrategyPosition,
    SignalType, StrategyType, StrategyState
)

logger = logging.getLogger(__name__)


@dataclass
class BreakoutConfig(StrategyConfig):
    """Enhanced Breakout Configuration"""
    
    # Breakout parameters
    lookback_period: int = 20               # Lookback for support/resistance
    breakout_threshold: float = 0.02        # Breakout threshold (2%)
    volume_confirmation: float = 1.5        # Volume confirmation multiplier
    
    # Position sizing
    base_position_pct: float = 0.03         # Base position size (3%)
    max_position_pct: float = 0.08          # Maximum position size (8%)
    
    # Risk management
    stop_loss_pct: float = 0.03             # Stop loss percentage (3%)
    profit_target_ratio: float = 2.0        # Profit target vs stop loss ratio
    
    # Asset universe
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])


class EnhancedBreakoutStrategy(EnhancedBaseStrategy):
    """Enhanced Breakout Strategy with ISystemComponent Integration"""
    
    def __init__(self, config: BreakoutConfig):
        """Initialize enhanced breakout strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: BreakoutConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🧠 Enhanced Breakout Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Breakout components for {self.strategy_id}...")
            
            if not self.config.symbols:
                logger.error("❌ No symbols configured for breakout strategy")
                return False
            
            self._initialize_data_structures()
            
            logger.info(f"✅ Breakout components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Breakout component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Breakout operations for {self.strategy_id}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Breakout operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Breakout operations for {self.strategy_id}...")
            await self._close_all_positions()
            logger.info(f"✅ Breakout operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Breakout operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            return {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'indicators_calculated': len(self.indicators)
            }
            
        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        return {
            'strategy_type': 'Enhanced Breakout',
            'symbols_count': len(self.config.symbols),
            'lookback_period': self.config.lookback_period,
            'breakout_threshold': self.config.breakout_threshold,
            'volume_confirmation': self.config.volume_confirmation
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            if self.config.breakout_threshold <= 0:
                logger.error("Breakout threshold must be positive")
                return False
            
            if self.config.lookback_period < 5:
                logger.error("Lookback period must be at least 5")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================
    
    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Generate breakout signals"""
        
        start_time = datetime.now()
        signals = []
        
        try:
            # Update market data
            self._update_market_data(market_data)
            
            # Calculate indicators
            self._calculate_indicators()
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.lookback_period:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Generated {len(signals)} Breakout signals in {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""
        
        try:
            self._update_market_data(market_data)
            await self._check_exit_conditions()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            base_size = self.config.base_position_pct
            confidence_multiplier = signal.confidence
            return min(base_size * confidence_multiplier, self.config.max_position_pct)
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals for a specific symbol"""
        
        signals = []
        
        try:
            # Skip if already have position
            if symbol in self.active_positions:
                return signals
            
            if symbol not in self.indicators:
                return signals
            
            indicators = self.indicators[symbol]
            current_data = self.market_data[symbol].iloc[-1]
            
            # Get breakout levels
            resistance = indicators['resistance'].iloc[-1] if len(indicators['resistance']) > 0 else 0
            support = indicators['support'].iloc[-1] if len(indicators['support']) > 0 else 0
            volume_ratio = indicators['volume_ratio'].iloc[-1] if len(indicators['volume_ratio']) > 0 else 1
            
            current_price = current_data['close']
            
            # Check for bullish breakout
            if (current_price > resistance * (1 + self.config.breakout_threshold) and
                volume_ratio > self.config.volume_confirmation):
                
                confidence = min(0.9, volume_ratio / self.config.volume_confirmation)
                
                signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=0.8,
                    confidence=confidence,
                    quantity=self.config.base_position_pct,
                    timestamp=datetime.now(),
                    metadata={
                        'signal_reason': 'bullish_breakout',
                        'resistance_level': resistance,
                        'breakout_price': current_price,
                        'volume_ratio': volume_ratio
                    }
                )
                signals.append(signal)
                
                # Track position entry
                self._track_position_entry(symbol, signal)
            
            # Check for bearish breakout
            elif (current_price < support * (1 - self.config.breakout_threshold) and
                  volume_ratio > self.config.volume_confirmation):
                
                confidence = min(0.9, volume_ratio / self.config.volume_confirmation)
                
                signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=0.8,
                    confidence=confidence,
                    quantity=self.config.base_position_pct,
                    timestamp=datetime.now(),
                    metadata={
                        'signal_reason': 'bearish_breakout',
                        'support_level': support,
                        'breakout_price': current_price,
                        'volume_ratio': volume_ratio
                    }
                )
                signals.append(signal)
                
                # Track position entry
                self._track_position_entry(symbol, signal)
            
            return signals
            
        except Exception as e:
            self._log_error(f"Symbol signal generation failed for {symbol}", e)
            return []
    
    # ========================================
    # INDICATOR CALCULATION METHODS
    # ========================================
    
    def _calculate_indicators(self) -> None:
        """Calculate technical indicators for all symbols"""
        
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.indicators[symbol] = self._calculate_symbol_indicators(symbol)
    
    def _calculate_symbol_indicators(self, symbol: str) -> Dict[str, pd.Series]:
        """Calculate indicators for a specific symbol"""
        
        try:
            data = self.market_data[symbol]
            indicators = {}
            
            # Calculate support and resistance levels
            high_prices = data['high']
            low_prices = data['low']
            volume = data['volume']
            
            # Rolling max/min for support/resistance
            indicators['resistance'] = high_prices.rolling(self.config.lookback_period).max()
            indicators['support'] = low_prices.rolling(self.config.lookback_period).min()
            
            # Volume ratio
            volume_ma = volume.rolling(self.config.lookback_period).mean()
            indicators['volume_ratio'] = volume / volume_ma
            
            return indicators
            
        except Exception as e:
            logger.error(f"Indicator calculation failed for {symbol}: {e}")
            return {}
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        
        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        
        self.market_data.clear()
        self.indicators.clear()
        self.active_positions.clear()
    
    def _track_position_entry(self, symbol: str, signal: StrategySignal) -> None:
        """Track position entry for exit management"""
        
        try:
            entry_price = signal.metadata.get('breakout_price', 0)
            
            # Calculate stop loss and profit target
            if signal.signal_type == SignalType.BUY:
                stop_loss = entry_price * (1 - self.config.stop_loss_pct)
                profit_target = entry_price * (1 + self.config.stop_loss_pct * self.config.profit_target_ratio)
            else:  # SELL
                stop_loss = entry_price * (1 + self.config.stop_loss_pct)
                profit_target = entry_price * (1 - self.config.stop_loss_pct * self.config.profit_target_ratio)
            
            # Track position
            self.active_positions[symbol] = {
                'signal_type': signal.signal_type,
                'entry_time': signal.timestamp,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'profit_target': profit_target,
                'quantity': signal.quantity
            }
            
            logger.info(f"📈 Breakout position tracked for {symbol}: Entry=${entry_price:.2f}")
            
        except Exception as e:
            self._log_error(f"Position tracking failed for {symbol}", e)
    
    async def _check_exit_conditions(self) -> None:
        """Check exit conditions for active positions"""
        
        try:
            positions_to_close = []
            
            for symbol in list(self.active_positions.keys()):
                if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    position = self.active_positions[symbol]
                    
                    should_exit = False
                    exit_reason = ""
                    
                    # Check stop loss
                    if position['signal_type'] == SignalType.BUY and current_price <= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif position['signal_type'] == SignalType.SELL and current_price >= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                    
                    # Check profit target
                    if not should_exit:
                        if position['signal_type'] == SignalType.BUY and current_price >= position['profit_target']:
                            should_exit = True
                            exit_reason = "profit_target"
                        elif position['signal_type'] == SignalType.SELL and current_price <= position['profit_target']:
                            should_exit = True
                            exit_reason = "profit_target"
                    
                    if should_exit:
                        positions_to_close.append((symbol, exit_reason))
                        logger.info(f"📉 Exit condition met for {symbol}: {exit_reason}")
            
            # Close positions
            for symbol, reason in positions_to_close:
                await self._close_position(symbol, reason)
                
        except Exception as e:
            self._log_error("Exit condition check failed", e)
    
    async def _close_position(self, symbol: str, reason: str) -> None:
        """Close a specific position"""
        
        try:
            if symbol in self.active_positions:
                position = self.active_positions[symbol]
                
                # Create exit signal
                exit_signal = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.SELL if position['signal_type'] == SignalType.BUY else SignalType.BUY,
                    strength=1.0,
                    confidence=0.9,
                    quantity=position['quantity'],
                    timestamp=datetime.now(),
                    metadata={
                        'action': 'exit',
                        'exit_reason': reason,
                        'entry_price': position['entry_price']
                    }
                )
                
                # Submit to risk manager if available
                if self.risk_manager:
                    await self.risk_manager.process_signal(exit_signal)
                
                # Clean up tracking
                del self.active_positions[symbol]
                
                logger.info(f"🔄 Breakout position closed for {symbol}: {reason}")
                
        except Exception as e:
            self._log_error(f"Position close failed for {symbol}", e)
    
    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_breakout_summary(self) -> Dict[str, Any]:
        """Get comprehensive breakout strategy summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Breakout',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'performance_summary': self.get_performance_summary(),
            'position_details': {
                symbol: {
                    'signal_type': pos['signal_type'].value,
                    'entry_price': pos['entry_price'],
                    'stop_loss': pos['stop_loss'],
                    'profit_target': pos['profit_target']
                }
                for symbol, pos in self.active_positions.items()
            }
        }
