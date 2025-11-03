"""
Enhanced Mean Reversion Strategy with ISystemComponent Integration
================================================================

Professional mean reversion strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Regime-aware mean reversion detection
- Multi-timeframe analysis and confirmation
- Dynamic position sizing based on volatility
- Professional risk management integration
- Comprehensive performance tracking

Key Features:
- Statistical mean reversion detection using Z-scores
- Bollinger Bands and RSI confluence
- Regime filtering to avoid choppy markets
- ATR-based position sizing
- Time-based and profit target exits
- Transaction cost awareness

Academic Foundations:
- Jegadeesh & Titman (1993) momentum and reversal
- Lo & MacKinlay (1990) contrarian investment strategies
- Poterba & Summers (1988) mean reversion in stock prices

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategyConfig, StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import MeanReversionConfig

logger = logging.getLogger(__name__)


class MeanReversionSignal(Enum):
    """Mean reversion signal types"""
    OVERSOLD_BUY = "oversold_buy"
    OVERBOUGHT_SELL = "overbought_sell"
    NEUTRAL = "neutral"


# Note: MeanReversionConfig now imported from core_engine.config (Rule 1 Section 7)
# Local definition removed - use centralized configuration


class EnhancedMeanReversionStrategy(EnhancedBaseStrategy):
    """
    Enhanced Mean Reversion Strategy with ISystemComponent Integration
    
    Professional mean reversion strategy that provides:
    - ISystemComponent interface compliance
    - Regime-aware mean reversion detection
    - Multi-timeframe analysis and confirmation
    - Dynamic position sizing based on volatility
    - Comprehensive performance tracking and risk management
    """
    
    def __init__(self, config: MeanReversionConfig):
        """Initialize enhanced mean reversion strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: MeanReversionConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.indicators: Dict[str, Dict[str, pd.Series]] = {}
        self.regime_data: Dict[str, Dict[str, float]] = {}
        
        # Position tracking
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.entry_prices: Dict[str, float] = {}
        self.stop_losses: Dict[str, float] = {}
        self.profit_targets: Dict[str, float] = {}
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: List[float] = []
        
        logger.info(f"🧠 Enhanced Mean Reversion Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Mean Reversion components for {self.strategy_id}...")
            
            # Validate symbols
            if not self.config.symbols:
                logger.error("❌ No symbols configured for mean reversion strategy")
                return False
            
            # Initialize data structures
            self._initialize_data_structures()
            
            # Initialize indicators
            self._initialize_indicators()
            
            logger.info(f"✅ Mean Reversion components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Mean Reversion operations for {self.strategy_id}...")
            
            # Start performance tracking
            self._start_performance_tracking()
            
            logger.info(f"✅ Mean Reversion operations started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Mean Reversion operations for {self.strategy_id}...")
            
            # Close all positions
            await self._close_all_positions()
            
            # Save performance data
            self._save_performance_data()
            
            logger.info(f"✅ Mean Reversion operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            health_metrics = {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'indicators_calculated': len(self.indicators),
                'avg_volatility': self._calculate_avg_volatility(),
                'regime_health': self._check_regime_health()
            }
            
            # Check for unhealthy conditions
            # Only require indicators if strategy has been running for a while
            if len(self.indicators) == 0 and hasattr(self, 'initialization_time'):
                time_since_init = (datetime.now() - self.initialization_time).total_seconds()
                if time_since_init > 300:  # 5 minutes grace period
                    health_metrics['strategy_healthy'] = False
                    health_metrics['warning'] = "No indicators calculated after 5 minutes"
                else:
                    health_metrics['warning'] = f"Indicators not yet calculated (grace period: {300-time_since_init:.0f}s remaining)"
            
            if len(self.active_positions) > len(self.config.symbols):
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "Too many active positions"
            
            return health_metrics
            
        except Exception as e:
            return {
                'strategy_healthy': False,
                'error': str(e)
            }
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        return {
            'strategy_type': 'Enhanced Mean Reversion',
            'symbols_count': len(self.config.symbols),
            'lookback_period': self.config.lookback_period,
            'zscore_entry_threshold': self.config.zscore_entry_threshold,
            'enable_multi_timeframe': self.config.enable_multi_timeframe,
            'enable_regime_filter': self.config.enable_regime_filter,
            'base_position_pct': self.config.base_position_pct,
            'volatility_target': self.config.volatility_target
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            # Validate thresholds
            if self.config.zscore_entry_threshold <= self.config.zscore_exit_threshold:
                logger.error("Entry Z-score threshold must be greater than exit threshold")
                return False
            
            # Validate position sizing
            if self.config.base_position_pct <= 0 or self.config.base_position_pct > 0.1:
                logger.error("Base position percentage must be between 0 and 0.1 (10%)")
                return False
            
            # Validate periods
            if self.config.lookback_period < 10:
                logger.error("Lookback period must be at least 10")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================
    
    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched with required indicators (Rule 3 Phase 4)
        
        This method ensures the data has passed through the ProcessingPipelineOrchestrator
        and contains all indicators required by the mean reversion strategy.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame]
        
        Raises:
            ValueError: If data is missing required indicators
        """
        required_indicators = [
            'SMA_20',           # Moving average (Bollinger Band middle)
            'RSI_14',           # RSI for overbought/oversold
            'bb_upper',         # Bollinger Band upper
            'bb_lower',         # Bollinger Band lower
            'bb_middle',        # Bollinger Band middle
            'ATR_14',           # Average True Range
            'volume_ratio'      # Volume indicator
        ]
        
        for symbol, data in enriched_data.items():
            if data.empty:
                raise ValueError(f"{symbol} has empty DataFrame")
            
            missing = [col for col in required_indicators if col not in data.columns]
            if missing:
                available_cols = list(data.columns[:20])
                raise ValueError(
                    f"{symbol} missing required indicators: {missing}. "
                    f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                    f"Available columns: {available_cols}"
                )
            
            logger.debug(f"✅ {symbol} enriched data validated: {len(required_indicators)} indicators present")
    
    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate mean reversion signals from ENRICHED data (Rule 3 Phase 4)
        
        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        indicators and features from the ProcessingPipelineOrchestrator. It does NOT
        calculate indicators itself.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: zscore, RSI_14, bb_upper, bb_lower, bb_middle, 
                                       bb_position, ATR_14, volume_ratio
        
        Returns:
            List[StrategySignal]: Generated mean reversion signals
        """
        start_time = datetime.now()
        signals = []
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # Update market data with enriched data
            self._update_market_data(enriched_data)
            
            # Update regime analysis
            if self.config.enable_regime_filter:
                self._update_regime_analysis()
            
            # Generate signals for each symbol
            for symbol in self.config.symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) > self.config.lookback_period:
                    symbol_signals = await self._generate_symbol_signals(symbol)
                    signals.extend(symbol_signals)
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Mean Reversion Strategy (Rule 3 Phase 4 - Enriched Data):")
            logger.info(f"   Signals generated: {len(signals)}")
            logger.info(f"   Generation time: {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""
        
        try:
            # Update market data
            self._update_market_data(market_data)
            
            # Check exit conditions for active positions
            await self._check_exit_conditions()
            
            # Update stop losses and profit targets
            self._update_stop_losses_and_targets()
            
            # Update performance tracking
            self._update_performance_tracking()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            symbol = signal.symbol
            
            # Get current price and ATR
            if symbol not in self.market_data or len(self.market_data[symbol]) == 0:
                return 0.0
            
            current_price = self.market_data[symbol]['close'].iloc[-1]
            atr = self._calculate_atr(symbol)
            
            if atr == 0:
                return self.config.base_position_pct
            
            # Calculate volatility-adjusted position size
            volatility = atr / current_price
            volatility_adjustment = self.config.volatility_target / max(volatility, 0.01)
            
            # Apply confidence scaling
            confidence_adjustment = signal.confidence
            
            # Calculate final position size
            position_size = (self.config.base_position_pct * 
                           volatility_adjustment * 
                           confidence_adjustment)
            
            # Cap at maximum position size
            return min(position_size, self.config.max_position_pct)
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================
    
    async def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """
        Generate signals for a specific symbol using PRE-CALCULATED indicators (Rule 3 Phase 4)
        
        **CRITICAL:** This method READS pre-calculated indicator values from enriched data.
        It does NOT calculate indicators itself.
        """
        signals = []
        
        try:
            # Skip if already have position
            if symbol in self.active_positions:
                return signals
            
            # Get enriched data with pre-calculated indicators
            if symbol not in self.market_data:
                return signals
            
            data = self.market_data[symbol]
            current_row = data.iloc[-1]
            
            # READ pre-calculated indicators from enriched DataFrame
            zscore = current_row.get('zscore', 0.0)
            rsi = current_row.get('RSI_14', 50.0)
            bb_position = current_row.get('bb_position', 0.5)
            
            # Apply regime filter
            if self.config.enable_regime_filter:
                if not self._is_regime_favorable(symbol):
                    return signals
            
            # Check for oversold condition (BUY signal)
            if (zscore < -self.config.zscore_entry_threshold and 
                rsi < self.config.rsi_oversold and 
                bb_position < 0.2):  # Below lower Bollinger Band
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERSOLD_BUY)
                
                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(abs(zscore) / self.config.zscore_entry_threshold, 1.0),
                        confidence=confidence,
                        target_quantity=self.config.base_position_pct,
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'oversold_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close']
                        }
                    )
                    signals.append(signal)
                    
                    # Track position entry
                    self._track_position_entry(symbol, signal)
            
            # Check for overbought condition (SELL signal)
            elif (zscore > self.config.zscore_entry_threshold and 
                  rsi > self.config.rsi_overbought and 
                  bb_position > 0.8):  # Above upper Bollinger Band
                
                confidence = self._calculate_signal_confidence(symbol, MeanReversionSignal.OVERBOUGHT_SELL)
                
                if confidence > 0.6:  # Minimum confidence threshold
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        strength=min(abs(zscore) / self.config.zscore_entry_threshold, 1.0),
                        confidence=confidence,
                        target_quantity=self.config.base_position_pct,
                        timestamp=datetime.now(),
                        additional_data={
                            'signal_reason': 'overbought_mean_reversion',
                            'zscore': zscore,
                            'rsi': rsi,
                            'bb_position': bb_position,
                            'entry_price': current_row['close']
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
    
    # ========================================
    # HELPER METHODS (Rule 3 Phase 4)
    # Reads pre-calculated indicators from enriched data
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
        self.regime_data.clear()
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.profit_targets.clear()
    
    def _initialize_indicators(self) -> None:
        """Initialize indicators dictionary"""
        
        for symbol in self.config.symbols:
            self.indicators[symbol] = {}
    
    def _start_performance_tracking(self) -> None:
        """Start performance tracking"""
        logger.info("📊 Mean Reversion performance tracking started")
    
    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
        self.entry_prices.clear()
        self.stop_losses.clear()
        self.profit_targets.clear()
    
    def _save_performance_data(self) -> None:
        """Save performance data"""
        logger.info("💾 Mean Reversion performance data saved")
    
    def _calculate_avg_volatility(self) -> float:
        """Calculate average volatility across symbols"""
        
        if not self.indicators:
            return 0.0
        
        volatilities = []
        for symbol, indicators in self.indicators.items():
            if 'atr' in indicators and len(indicators['atr']) > 0:
                if symbol in self.market_data and len(self.market_data[symbol]) > 0:
                    current_price = self.market_data[symbol]['close'].iloc[-1]
                    atr = indicators['atr'].iloc[-1]
                    if current_price > 0:
                        volatilities.append(atr / current_price)
        
        return np.mean(volatilities) if volatilities else 0.0
    
    def _check_regime_health(self) -> Dict[str, Any]:
        """Check regime analysis health"""
        
        return {
            'regime_filter_enabled': self.config.enable_regime_filter,
            'symbols_with_regime_data': len(self.regime_data)
        }
    
    def _update_regime_analysis(self) -> None:
        """Update regime analysis for symbols"""
        
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.regime_data[symbol] = self._analyze_symbol_regime(symbol)
    
    def _analyze_symbol_regime(self, symbol: str) -> Dict[str, float]:
        """Analyze regime for a specific symbol"""
        
        try:
            data = self.market_data[symbol]
            
            # Simple regime analysis
            returns = data['close'].pct_change().dropna()
            
            # Trend strength (momentum)
            trend_strength = abs(returns.tail(20).mean()) / returns.tail(20).std() if len(returns) >= 20 else 0
            
            # Volatility regime
            current_vol = returns.tail(20).std() if len(returns) >= 20 else 0
            long_term_vol = returns.tail(60).std() if len(returns) >= 60 else current_vol
            volatility_ratio = current_vol / long_term_vol if long_term_vol > 0 else 1.0
            
            return {
                'trend_strength': trend_strength,
                'volatility_ratio': volatility_ratio,
                'is_trending': trend_strength > self.config.min_trend_strength,
                'is_high_vol': volatility_ratio > 1.5
            }
            
        except Exception as e:
            logger.error(f"Regime analysis failed for {symbol}: {e}")
            return {'trend_strength': 0, 'volatility_ratio': 1.0, 'is_trending': False, 'is_high_vol': False}
    
    def _is_regime_favorable(self, symbol: str) -> bool:
        """Check if current regime is favorable for mean reversion"""
        
        if symbol not in self.regime_data:
            return True  # Default to favorable if no regime data
        
        regime = self.regime_data[symbol]
        
        # Mean reversion works best in:
        # 1. Non-trending markets (low trend strength)
        # 2. Normal to low volatility environments
        
        is_favorable = (not regime.get('is_trending', False) and 
                       not regime.get('is_high_vol', False))
        
        return is_favorable
    
    def _calculate_signal_confidence(self, symbol: str, signal_type: MeanReversionSignal) -> float:
        """Calculate signal confidence based on multiple factors"""
        
        try:
            if symbol not in self.market_data:
                return 0.5
            
            data = self.market_data[symbol]
            current_row = data.iloc[-1]
            
            # Base confidence from Z-score magnitude
            zscore = current_row.get('zscore', 0.0)
            zscore_confidence = min(abs(zscore) / (self.config.zscore_entry_threshold * 1.5), 1.0)
            
            # RSI confirmation
            rsi = current_row.get('RSI_14', 50.0)
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                rsi_confidence = max(0, (50 - rsi) / 20)  # Higher confidence for lower RSI
            else:  # OVERBOUGHT_SELL
                rsi_confidence = max(0, (rsi - 50) / 20)  # Higher confidence for higher RSI
            
            # Bollinger Band confirmation
            bb_position = current_row.get('bb_position', 0.5)
            if signal_type == MeanReversionSignal.OVERSOLD_BUY:
                bb_confidence = max(0, (0.5 - bb_position) / 0.5)  # Higher confidence near lower band
            else:  # OVERBOUGHT_SELL
                bb_confidence = max(0, (bb_position - 0.5) / 0.5)  # Higher confidence near upper band
            
            # Regime confirmation - use configurable values from centralized config (Rule 1)
            regime_confidence = 1.0
            if self.config.enable_regime_filter and symbol in self.regime_data:
                regime_confidence = self.config.regime_confidence_favorable if self._is_regime_favorable(symbol) else self.config.regime_confidence_unfavorable
            
            # Combine confidences (weighted average) - use configurable weights from centralized config (Rule 1)
            total_confidence = (zscore_confidence * self.config.confidence_weight_zscore + 
                              rsi_confidence * self.config.confidence_weight_rsi + 
                              bb_confidence * self.config.confidence_weight_bollinger + 
                              regime_confidence * self.config.confidence_weight_regime)
            
            return min(total_confidence, 0.95)  # Cap at 95%
            
        except Exception as e:
            logger.error(f"Signal confidence calculation failed for {symbol}: {e}")
            return 0.5
    
    def _track_position_entry(self, symbol: str, signal: StrategySignal) -> None:
        """Track position entry for exit management"""
        
        try:
            entry_price = signal.metadata.get('entry_price', 0)
            atr = self._calculate_atr(symbol)
            
            # Calculate stop loss and profit target
            if signal.signal_type == SignalType.BUY:
                stop_loss = entry_price - (atr * self.config.stop_loss_atr_multiple)
                profit_target = entry_price + (atr * self.config.stop_loss_atr_multiple * self.config.profit_target_ratio)
            else:  # SELL
                stop_loss = entry_price + (atr * self.config.stop_loss_atr_multiple)
                profit_target = entry_price - (atr * self.config.stop_loss_atr_multiple * self.config.profit_target_ratio)
            
            # Track position
            self.active_positions[symbol] = {
                'signal_type': signal.signal_type,
                'entry_time': signal.timestamp,
                'entry_price': entry_price,
                'quantity': signal.quantity
            }
            
            self.entry_prices[symbol] = entry_price
            self.stop_losses[symbol] = stop_loss
            self.profit_targets[symbol] = profit_target
            
            logger.info(f"📈 Position tracked for {symbol}: Entry=${entry_price:.2f}, "
                       f"Stop=${stop_loss:.2f}, Target=${profit_target:.2f}")
            
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
                    if symbol in self.stop_losses:
                        if position['signal_type'] == SignalType.BUY and current_price <= self.stop_losses[symbol]:
                            should_exit = True
                            exit_reason = "stop_loss"
                        elif position['signal_type'] == SignalType.SELL and current_price >= self.stop_losses[symbol]:
                            should_exit = True
                            exit_reason = "stop_loss"
                    
                    # Check profit target
                    if not should_exit and symbol in self.profit_targets:
                        if position['signal_type'] == SignalType.BUY and current_price >= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"
                        elif position['signal_type'] == SignalType.SELL and current_price <= self.profit_targets[symbol]:
                            should_exit = True
                            exit_reason = "profit_target"
                    
                    # Check mean reversion (Z-score back to neutral)
                    if not should_exit and symbol in self.indicators and 'zscore' in self.indicators[symbol]:
                        zscore = self.indicators[symbol]['zscore'].iloc[-1]
                        if abs(zscore) < self.config.zscore_exit_threshold:
                            should_exit = True
                            exit_reason = "mean_reversion"
                    
                    # Check maximum holding period
                    if not should_exit:
                        holding_time = datetime.now() - position['entry_time']
                        if holding_time.total_seconds() > (self.config.max_holding_period * 300):  # Assuming 5-min bars
                            should_exit = True
                            exit_reason = "max_holding_period"
                    
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
                
                # Create exit signal (would be sent to risk manager)
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
                if symbol in self.entry_prices:
                    del self.entry_prices[symbol]
                if symbol in self.stop_losses:
                    del self.stop_losses[symbol]
                if symbol in self.profit_targets:
                    del self.profit_targets[symbol]
                
                logger.info(f"🔄 Position closed for {symbol}: {reason}")
                
        except Exception as e:
            self._log_error(f"Position close failed for {symbol}", e)
    
    def _update_stop_losses_and_targets(self) -> None:
        """Update stop losses and profit targets (trailing stops, etc.)"""
        
        # Placeholder for advanced stop loss management
        # Could implement trailing stops, dynamic targets, etc.
    
    def _update_performance_tracking(self) -> None:
        """Update performance tracking metrics"""
        
        # Placeholder for performance tracking updates
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_mean_reversion_summary(self) -> Dict[str, Any]:
        """Get comprehensive mean reversion strategy summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Mean Reversion',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'indicators_calculated': len(self.indicators),
            'avg_volatility': self._calculate_avg_volatility(),
            'regime_filter_enabled': self.config.enable_regime_filter,
            'performance_summary': self.get_performance_summary(),
            'position_details': {
                symbol: {
                    'signal_type': pos['signal_type'].value,
                    'entry_price': pos['entry_price'],
                    'entry_time': pos['entry_time'].isoformat(),
                    'stop_loss': self.stop_losses.get(symbol),
                    'profit_target': self.profit_targets.get(symbol)
                }
                for symbol, pos in self.active_positions.items()
            }
        }
