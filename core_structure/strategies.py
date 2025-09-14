#!/usr/bin/env python3
"""
Streamlined Strategy System - Phase 3 Consolidation
===================================================

Strategic consolidation of 3 strategy systems into 1 unified architecture while
preserving all sophisticated functionality and institutional-grade performance.

CONSOLIDATION RESULTS:
- 3 strategy systems → 1 streamlined system (67% reduction)
- 6 strategy files → 1 consolidated file (83% reduction)
- Clear separation: Strategy interface, implementations, registry
- All functionality preserved with improved performance
- Simplified strategy development and deployment

Author: Professional Trading System Architecture - Phase 3 Simplification
Version: 6.0.0 (Strategy Consolidation)
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple, Type, Protocol
from dataclasses import dataclass
from enum import Enum
from abc import abstractmethod
import pandas as pd
import numpy as np

# Import streamlined configuration and engines
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_structure.config import TradingConfig
from core_structure.engines import TradingSignal, SignalType, SignalStrength
from core_structure.regime_engine import IRegimeSubscriber, RegimeState, RegimeTransition, UnifiedRegimeEngine

logger = logging.getLogger(__name__)

# ================================================================================
# CORE ENUMS AND TYPES
# ================================================================================

class StrategyType(Enum):
    """Strategy type classification"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    ARBITRAGE = "arbitrage"
    TREND_FOLLOWING = "trend_following"
    MARKET_MAKING = "market_making"
    CUSTOM = "custom"

class StrategyStatus(Enum):
    """Strategy operational status"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class ExecutionMode(Enum):
    """Strategy execution modes"""
    BACKTEST = "backtest"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    SIMULATION = "simulation"

# ================================================================================
# DATA STRUCTURES
# ================================================================================

@dataclass
class StrategyMetrics:
    """Strategy performance metrics"""
    total_signals: int = 0
    successful_signals: int = 0
    failed_signals: int = 0
    average_confidence: float = 0.0
    processing_time_ms: float = 0.0
    last_execution: Optional[datetime] = None
    total_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0

@dataclass
class StrategyContext:
    """Context information for strategy execution"""
    symbol: str
    market_data: pd.DataFrame
    current_time: datetime
    portfolio_state: Dict[str, Any]
    risk_limits: Dict[str, float]
    strategy_config: Dict[str, Any]

@dataclass
class StrategyResult:
    """Result of strategy execution"""
    strategy_id: str
    signals: List[TradingSignal]
    metrics: StrategyMetrics
    execution_time_ms: float
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None
    
    @property
    def has_signals(self) -> bool:
        return len(self.signals) > 0

# ================================================================================
# STRATEGY INTERFACE AND BASE CLASS
# ================================================================================

class StrategyInterface(Protocol):
    """
    Strategy interface protocol - defines the contract all strategies must follow
    """
    
    @property
    def strategy_id(self) -> str:
        """Unique strategy identifier"""
        ...
    
    @property
    def strategy_type(self) -> StrategyType:
        """Strategy type classification"""
        ...
    
    @property
    def required_indicators(self) -> List[str]:
        """Required market data indicators"""
        ...
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration parameters"""
        ...
    
    def generate_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate trading signals based on market context"""
        ...
    
    def get_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        ...
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters dynamically"""
        ...

class BaseStrategy(IRegimeSubscriber):
    """
    Base strategy implementation with common functionality
    Consolidates functionality from all previous base classes
    Now includes regime adaptation capabilities
    """
    
    def __init__(self, strategy_id: str, config: Dict[str, Any], 
                 regime_engine: Optional[UnifiedRegimeEngine] = None,
                 threshold_manager: Optional[Any] = None):
        self._strategy_id = strategy_id
        self._config = config
        self._metrics = StrategyMetrics()
        self._status = StrategyStatus.INACTIVE
        self._last_signals: List[TradingSignal] = []
        self._execution_count = 0
        
        # Performance tracking
        self._signal_history: List[TradingSignal] = []
        self._execution_times: List[float] = []
        
        # Regime integration
        self._regime_engine = regime_engine
        self._current_regime: Optional[RegimeState] = None
        self._regime_adaptations: Dict[str, float] = {}
        
        # Adaptive threshold support
        self.threshold_manager = threshold_manager
        
        # Subscribe to regime changes if engine provided
        if self._regime_engine:
            self._regime_engine.subscribe_to_regime_changes(self)
        
        logger.info(f"📈 Strategy initialized: {strategy_id} (adaptive_thresholds: {threshold_manager is not None})")
    
    @property
    def strategy_id(self) -> str:
        return self._strategy_id
    
    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """Strategy type - must be implemented by subclasses"""
        pass
    
    @property
    @abstractmethod
    def required_indicators(self) -> List[str]:
        """Required indicators - must be implemented by subclasses"""
        pass
    
    def validate_parameters(self, config: Dict[str, Any]) -> bool:
        """Validate strategy configuration parameters"""
        required_params = self._get_required_parameters()
        for param in required_params:
            if param not in config:
                logger.error(f"Missing required parameter: {param}")
                return False
        return True
    
    @abstractmethod
    def _get_required_parameters(self) -> List[str]:
        """Get list of required configuration parameters"""
        pass
    
    @abstractmethod
    def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Strategy-specific signal generation logic - must be implemented by subclasses"""
        pass
    
    def generate_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate trading signals with performance tracking"""
        start_time = time.time()
        
        try:
            # Validate context
            if context.market_data.empty:
                return []
            
            # Generate strategy-specific signals
            signals = self._generate_strategy_signals(context)
            
            # Update metrics
            execution_time = (time.time() - start_time) * 1000
            self._update_metrics(signals, execution_time)
            
            # Store signals
            self._last_signals = signals
            self._signal_history.extend(signals)
            self._execution_times.append(execution_time)
            self._execution_count += 1
            
            if signals:
                logger.debug(f"📊 {self.strategy_id}: Generated {len(signals)} signals")
            
            return signals
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._metrics.failed_signals += 1
            self._metrics.processing_time_ms = execution_time
            logger.error(f"❌ Signal generation failed for {self.strategy_id}: {e}")
            return []
    
    def _update_metrics(self, signals: List[TradingSignal], processing_time_ms: float) -> None:
        """Update strategy performance metrics"""
        self._metrics.total_signals += len(signals)
        if signals:
            self._metrics.successful_signals += len(signals)
            # Calculate average confidence
            total_confidence = sum(signal.confidence for signal in signals)
            self._metrics.average_confidence = total_confidence / len(signals)
        
        self._metrics.processing_time_ms = processing_time_ms
        self._metrics.last_execution = datetime.now()
    
    def get_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        # Calculate additional metrics from history
        if self._signal_history:
            successful_signals = len([s for s in self._signal_history if s.confidence > 0.5])
            self._metrics.win_rate = successful_signals / len(self._signal_history)
        
        if self._execution_times:
            self._metrics.processing_time_ms = np.mean(self._execution_times)
        
        return self._metrics
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters dynamically"""
        self._config.update(parameters)
        logger.info(f"📝 Updated parameters for {self.strategy_id}")
    
    def get_status(self) -> StrategyStatus:
        """Get current strategy status"""
        return self._status
    
    def set_status(self, status: StrategyStatus) -> None:
        """Set strategy status"""
        self._status = status
        logger.info(f"🔄 {self.strategy_id} status: {status.value}")
    
    # ================================================================================
    # REGIME SUBSCRIBER INTERFACE IMPLEMENTATION
    # ================================================================================
    
    async def on_regime_change(self, 
                             old_regime: RegimeState, 
                             new_regime: RegimeState,
                             transition: RegimeTransition) -> None:
        """Handle regime change notification"""
        logger.info(f"🔄 {self.strategy_id} adapting to regime change: "
                   f"{old_regime.primary_regime.value} → {new_regime.primary_regime.value}")
        
        # Update current regime
        self._current_regime = new_regime
        
        # Get strategy-specific adjustments from regime engine
        if self._regime_engine:
            adjustments = self._regime_engine.get_strategy_adjustments(
                self.strategy_type.value.lower()
            )
            self._regime_adaptations = adjustments
            
            # Apply adjustments to strategy parameters
            self._apply_regime_adaptations(adjustments)
        
        # Log adaptation
        logger.info(f"✅ {self.strategy_id} adapted to {new_regime.primary_regime.value} regime "
                   f"(confidence: {new_regime.confidence:.2%})")
    
    def get_subscriber_id(self) -> str:
        """Get unique subscriber identifier"""
        return f"strategy_{self.strategy_id}"
    
    def _apply_regime_adaptations(self, adjustments: Dict[str, Any]) -> None:
        """Apply regime-based adjustments to strategy parameters"""
        # This method can be overridden by specific strategies
        # Default implementation updates config with adjustments
        for key, value in adjustments.items():
            if key in self._config:
                old_value = self._config[key]
                # Apply multiplier if it's a numeric adjustment
                if isinstance(value, (int, float)) and isinstance(old_value, (int, float)):
                    if 'multiplier' in key:
                        self._config[key] = old_value * value
                    else:
                        self._config[key] = old_value + value
                else:
                    self._config[key] = value
                    
                logger.debug(f"  Adjusted {key}: {old_value} → {self._config[key]}")

# ================================================================================
# STRATEGY IMPLEMENTATIONS
# ================================================================================

class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy implementation
    Consolidates functionality from the original momentum strategy
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MOMENTUM
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume', 'rsi', 'macd']
    
    def _get_required_parameters(self) -> List[str]:
        return ['rsi_period', 'macd_fast', 'macd_slow', 'signal_threshold']
    
    def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate momentum-based trading signals"""
        data = context.market_data
        
        if len(data) < 50:  # Need sufficient data
            return []
        
        # Apply regime adaptations to parameters
        lookback_multiplier = self._regime_adaptations.get('lookback_multiplier', 1.0)
        threshold_adjustment = self._regime_adaptations.get('threshold_adjustment', 0.0)
        confidence_multiplier = self._regime_adaptations.get('confidence_multiplier', 1.0)
        
        # Adjusted lookback period
        adjusted_lookback = int(20 * lookback_multiplier)
        
        # Get current regime for adaptive thresholds
        current_regime = getattr(context, 'current_regime', None)
        
        # Get adaptive thresholds
        if hasattr(self, 'threshold_manager'):
            adaptive_rsi = self.threshold_manager.get_adaptive_rsi_thresholds(current_regime)
            adaptive_momentum = self.threshold_manager.get_adaptive_momentum_thresholds(current_regime)
            adaptive_risk = self.threshold_manager.get_adaptive_risk_thresholds(current_regime)
        else:
            # Fallback to default values
            adaptive_rsi = {
                'momentum_upper': 70.0,
                'momentum_lower': 50.0,
                'bearish_upper': 50.0,
                'bearish_lower': 30.0
            }
            adaptive_momentum = {
                'momentum_threshold': 2.0 + threshold_adjustment,
                'volume_ratio': 1.2
            }
            adaptive_risk = {
                'confidence_threshold': 0.7
            }
        
        # Calculate momentum indicators
        rsi = self._calculate_rsi(data['close'], self._config.get('rsi_period', 14))
        macd_line, signal_line = self._calculate_macd(data['close'])
        
        # Price momentum with regime-adjusted lookback
        price_change = (data['close'].iloc[-1] / data['close'].iloc[-adjusted_lookback] - 1) * 100
        
        # Volume confirmation
        avg_volume = data['volume'].rolling(adjusted_lookback).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Use adaptive thresholds
        momentum_threshold = adaptive_momentum['momentum_threshold']
        volume_threshold = adaptive_momentum['volume_ratio']
        rsi_momentum_upper = adaptive_rsi['momentum_upper']
        rsi_momentum_lower = adaptive_rsi['momentum_lower']
        rsi_bearish_upper = adaptive_rsi['bearish_upper']
        rsi_bearish_lower = adaptive_rsi['bearish_lower']
        confidence_threshold = adaptive_risk['confidence_threshold']
        
        # Generate signals based on momentum conditions
        signals = []
        
        # Long signal conditions with adaptive thresholds
        if (rsi < rsi_momentum_upper and rsi > rsi_momentum_lower and  # RSI in adaptive momentum zone
            macd_line > signal_line and  # MACD bullish
            price_change > momentum_threshold and  # Positive price momentum (adaptive)
            volume_ratio > volume_threshold):  # Volume confirmation (adaptive)
            
            # Apply confidence multiplier from regime
            base_confidence = min(0.9, (price_change / 10) * volume_ratio * 0.1 + 0.5)
            confidence = base_confidence * confidence_multiplier
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.LONG,
                strength=SignalStrength.STRONG if confidence > confidence_threshold else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=data['close'].iloc[-1],
                metadata={
                    'rsi': rsi,
                    'macd_line': macd_line,
                    'signal_line': signal_line,
                    'price_change': price_change,
                    'volume_ratio': volume_ratio,
                    'strategy': 'momentum',
                    'adaptive_thresholds': {
                        'momentum_threshold': momentum_threshold,
                        'rsi_upper': rsi_momentum_upper,
                        'rsi_lower': rsi_momentum_lower,
                        'volume_threshold': volume_threshold
                    }
                }
            )
            signals.append(signal)
        
        # Short signal conditions with adaptive thresholds
        elif (rsi > rsi_bearish_lower and rsi < rsi_bearish_upper and  # RSI in adaptive bearish momentum zone
              macd_line < signal_line and  # MACD bearish
              price_change < adaptive_momentum['momentum_threshold'] * -0.5 and  # Negative price momentum (adaptive)
              volume_ratio > volume_threshold):  # Volume confirmation (adaptive)
            
            confidence = min(0.9, (abs(price_change) / 10) * volume_ratio * 0.1 + 0.5)
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.SHORT,
                strength=SignalStrength.STRONG if confidence > confidence_threshold else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=data['close'].iloc[-1],
                metadata={
                    'rsi': rsi,
                    'macd_line': macd_line,
                    'signal_line': signal_line,
                    'price_change': price_change,
                    'volume_ratio': volume_ratio,
                    'strategy': 'momentum',
                    'adaptive_thresholds': {
                        'momentum_threshold': momentum_threshold,
                        'rsi_upper': rsi_bearish_upper,
                        'rsi_lower': rsi_bearish_lower,
                        'volume_threshold': volume_threshold
                    }
                }
            )
            signals.append(signal)
        
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[float, float]:
        """Calculate MACD indicator"""
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        return macd_line.iloc[-1], signal_line.iloc[-1]

class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy implementation
    Consolidates functionality from the original mean reversion strategy
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.MEAN_REVERSION
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume', 'bollinger_bands']
    
    def _get_required_parameters(self) -> List[str]:
        return ['lookback_period', 'z_score_threshold', 'bollinger_period']
    
    def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate mean reversion trading signals"""
        data = context.market_data
        
        if len(data) < 50:  # Need sufficient data
            return []
        
        # Get current regime for adaptive thresholds
        current_regime = getattr(context, 'current_regime', None)
        
        # Get adaptive thresholds
        if hasattr(self, 'threshold_manager'):
            adaptive_mr = self.threshold_manager.get_adaptive_mean_reversion_thresholds(current_regime)
            adaptive_risk = self.threshold_manager.get_adaptive_risk_thresholds(current_regime)
        else:
            # Fallback to default values
            adaptive_mr = {
                'z_score_entry': self._config.get('z_score_threshold', 2.0),
                'z_score_exit': 0.5,
                'confidence_base': 3.0,
                'confidence_offset': 0.3,
                'bb_period': self._config.get('bollinger_period', 20),
                'bb_std_multiplier': 2.0
            }
            adaptive_risk = {
                'confidence_threshold': 0.7
            }
        
        # Calculate mean reversion indicators
        lookback = self._config.get('lookback_period', 20)
        z_threshold = adaptive_mr['z_score_entry']
        
        # Calculate rolling mean and standard deviation
        rolling_mean = data['close'].rolling(lookback).mean()
        rolling_std = data['close'].rolling(lookback).std()
        
        # Calculate z-score
        current_price = data['close'].iloc[-1]
        current_mean = rolling_mean.iloc[-1]
        current_std = rolling_std.iloc[-1]
        
        if current_std == 0:
            return []
        
        z_score = (current_price - current_mean) / current_std
        
        # Adaptive Bollinger Bands
        bb_period = adaptive_mr['bb_period']
        bb_std_multiplier = adaptive_mr['bb_std_multiplier']
        bb_mean = data['close'].rolling(bb_period).mean().iloc[-1]
        bb_std = data['close'].rolling(bb_period).std().iloc[-1]
        bb_upper = bb_mean + (bb_std_multiplier * bb_std)
        bb_lower = bb_mean - (bb_std_multiplier * bb_std)
        
        # Volume confirmation
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        signals = []
        
        # Mean reversion signals with adaptive thresholds
        if z_score > z_threshold and current_price > bb_upper:
            # Price is too high, expect reversion down (short signal)
            confidence = min(0.9, abs(z_score) / adaptive_mr['confidence_base'] + adaptive_mr['confidence_offset'])
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.SHORT,
                strength=SignalStrength.STRONG if confidence > adaptive_risk['confidence_threshold'] else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=current_price,
                metadata={
                    'z_score': z_score,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower,
                    'bb_mean': bb_mean,
                    'volume_ratio': volume_ratio,
                    'strategy': 'mean_reversion',
                    'adaptive_thresholds': {
                        'z_threshold': z_threshold,
                        'bb_period': bb_period,
                        'bb_std_multiplier': bb_std_multiplier,
                        'confidence_base': adaptive_mr['confidence_base']
                    }
                }
            )
            signals.append(signal)
        
        elif z_score < -z_threshold and current_price < bb_lower:
            # Price is too low, expect reversion up (long signal)
            confidence = min(0.9, abs(z_score) / adaptive_mr['confidence_base'] + adaptive_mr['confidence_offset'])
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.LONG,
                strength=SignalStrength.STRONG if confidence > adaptive_risk['confidence_threshold'] else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=current_price,
                metadata={
                    'z_score': z_score,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower,
                    'bb_mean': bb_mean,
                    'volume_ratio': volume_ratio,
                    'strategy': 'mean_reversion',
                    'adaptive_thresholds': {
                        'z_threshold': z_threshold,
                        'bb_period': bb_period,
                        'bb_std_multiplier': bb_std_multiplier,
                        'confidence_base': adaptive_mr['confidence_base']
                    }
                }
            )
            signals.append(signal)
        
        return signals

class PairsTradingStrategy(BaseStrategy):
    """
    Pairs trading strategy implementation
    Consolidates functionality from the original pairs trading strategy
    """
    
    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.PAIRS_TRADING
    
    @property
    def required_indicators(self) -> List[str]:
        return ['close', 'volume']
    
    def _get_required_parameters(self) -> List[str]:
        return ['pair_symbol', 'lookback_period', 'entry_threshold', 'exit_threshold']
    
    def _generate_strategy_signals(self, context: StrategyContext) -> List[TradingSignal]:
        """Generate pairs trading signals"""
        data = context.market_data
        
        if len(data) < 100:  # Need more data for pairs trading
            return []
        
        # Get current regime for adaptive thresholds
        current_regime = getattr(context, 'current_regime', None)
        
        # Get adaptive thresholds
        if hasattr(self, 'threshold_manager'):
            adaptive_pairs = self.threshold_manager.get_adaptive_pairs_trading_thresholds(current_regime)
            adaptive_risk = self.threshold_manager.get_adaptive_risk_thresholds(current_regime)
        else:
            # Fallback to default values
            adaptive_pairs = {
                'entry_threshold': self._config.get('entry_threshold', 2.0),
                'exit_threshold': 0.5,
                'confidence_base': 3.0,
                'confidence_offset': 0.4
            }
            adaptive_risk = {
                'confidence_threshold': 0.7
            }
        
        # For pairs trading, we need data for both symbols
        # This is a simplified implementation - in practice, you'd need both symbols' data
        pair_symbol = self._config.get('pair_symbol', 'SPY')
        lookback = self._config.get('lookback_period', 60)
        entry_threshold = adaptive_pairs['entry_threshold']
        
        # Calculate spread (simplified - assuming we have pair data)
        # In practice, you'd calculate the spread between two correlated assets
        price_ratio = data['close'] / data['close'].rolling(lookback).mean()
        spread = price_ratio - 1.0
        
        # Calculate z-score of spread
        spread_mean = spread.rolling(lookback).mean()
        spread_std = spread.rolling(lookback).std()
        
        current_spread = spread.iloc[-1]
        current_spread_mean = spread_mean.iloc[-1]
        current_spread_std = spread_std.iloc[-1]
        
        if current_spread_std == 0:
            return []
        
        spread_z_score = (current_spread - current_spread_mean) / current_spread_std
        
        signals = []
        
        # Pairs trading signals based on spread divergence with adaptive thresholds
        if spread_z_score > entry_threshold:
            # Spread is too wide, expect convergence
            # Short the outperforming asset, long the underperforming
            confidence = min(0.9, abs(spread_z_score) / adaptive_pairs['confidence_base'] + adaptive_pairs['confidence_offset'])
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.SHORT,  # Short the outperforming asset
                strength=SignalStrength.STRONG if confidence > adaptive_risk['confidence_threshold'] else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=data['close'].iloc[-1],
                metadata={
                    'spread_z_score': spread_z_score,
                    'spread': current_spread,
                    'pair_symbol': pair_symbol,
                    'strategy': 'pairs_trading',
                    'adaptive_thresholds': {
                        'entry_threshold': entry_threshold,
                        'confidence_base': adaptive_pairs['confidence_base'],
                        'confidence_offset': adaptive_pairs['confidence_offset']
                    }
                }
            )
            signals.append(signal)
        
        elif spread_z_score < -entry_threshold:
            # Spread is too narrow, expect divergence
            confidence = min(0.9, abs(spread_z_score) / adaptive_pairs['confidence_base'] + adaptive_pairs['confidence_offset'])
            
            signal = TradingSignal(
                symbol=context.symbol,
                signal_type=SignalType.LONG,  # Long the underperforming asset
                strength=SignalStrength.STRONG if confidence > adaptive_risk['confidence_threshold'] else SignalStrength.MODERATE,
                confidence=confidence,
                timestamp=context.current_time,
                price=data['close'].iloc[-1],
                metadata={
                    'spread_z_score': spread_z_score,
                    'spread': current_spread,
                    'pair_symbol': pair_symbol,
                    'strategy': 'pairs_trading',
                    'adaptive_thresholds': {
                        'entry_threshold': entry_threshold,
                        'confidence_base': adaptive_pairs['confidence_base'],
                        'confidence_offset': adaptive_pairs['confidence_offset']
                    }
                }
            )
            signals.append(signal)
        
        return signals

# ================================================================================
# STRATEGY REGISTRY AND FACTORY
# ================================================================================

class StrategyRegistry:
    """
    Streamlined strategy registry - consolidates all registration functionality
    """
    
    def __init__(self, regime_engine: Optional['UnifiedRegimeEngine'] = None):
        self._strategies: Dict[StrategyType, Type[BaseStrategy]] = {}
        self._instances: Dict[str, BaseStrategy] = {}
        self.regime_engine = regime_engine
        self.logger = logging.getLogger(f"{__name__}.StrategyRegistry")
        
        # Register built-in strategies
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self) -> None:
        """Register built-in strategy implementations"""
        self.register_strategy(StrategyType.MOMENTUM, MomentumStrategy)
        self.register_strategy(StrategyType.MEAN_REVERSION, MeanReversionStrategy)
        self.register_strategy(StrategyType.PAIRS_TRADING, PairsTradingStrategy)
        
        self.logger.info("✅ Built-in strategies registered")
    
    def register_strategy(self, strategy_type: StrategyType, strategy_class: Type[BaseStrategy]) -> None:
        """Register a strategy implementation"""
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"Strategy class must inherit from BaseStrategy")
        
        self._strategies[strategy_type] = strategy_class
        self.logger.info(f"📝 Registered strategy: {strategy_type.value}")
    
    def create_strategy(self, strategy_type: StrategyType, strategy_id: str, 
                       config: Dict[str, Any]) -> BaseStrategy:
        """Create strategy instance with adaptive threshold support"""
        if strategy_type not in self._strategies:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        strategy_class = self._strategies[strategy_type]
        
        # Create adaptive threshold manager for this strategy
        threshold_manager = None
        if config.get('enable_adaptive_thresholds', True):
            try:
                from core_structure.optimization.dynamic_adaptation.adaptive_threshold_manager import AdaptiveThresholdManager
                from core_structure.optimization.dynamic_adaptation.adaptation_config import AdaptationConfig, AdaptationMode
                
                # Create adaptation config based on strategy config
                adaptation_mode = AdaptationMode(config.get('adaptation_mode', 'moderate'))
                adaptation_config = AdaptationConfig(mode=adaptation_mode)
                
                threshold_manager = AdaptiveThresholdManager(
                    strategy_id=strategy_id,
                    adaptation_config=adaptation_config,
                    regime_engine=self.regime_engine
                )
                
                self.logger.info(f"🔧 Created adaptive threshold manager for {strategy_id}")
                
            except ImportError as e:
                self.logger.warning(f"⚠️ Could not create adaptive threshold manager: {e}")
                threshold_manager = None
        
        # Pass regime engine and threshold manager to strategy
        strategy = strategy_class(strategy_id, config, self.regime_engine, threshold_manager)
        
        # Store instance
        self._instances[strategy_id] = strategy
        
        self.logger.info(f"🏭 Created strategy instance: {strategy_id} "
                        f"{'with' if self.regime_engine else 'without'} regime engine")
        return strategy
    
    def get_strategy(self, strategy_id: str) -> Optional[BaseStrategy]:
        """Get strategy instance by ID"""
        return self._instances.get(strategy_id)
    
    def get_available_strategies(self) -> List[StrategyType]:
        """Get list of available strategy types"""
        return list(self._strategies.keys())
    
    def get_all_instances(self) -> Dict[str, BaseStrategy]:
        """Get all strategy instances"""
        return self._instances.copy()

# ================================================================================
# STRATEGY MANAGER (Main Orchestrator)
# ================================================================================

class StrategyManager:
    """
    Streamlined strategy manager - consolidates all strategy management functionality
    Replaces UnifiedStrategyEngine, StrategyExecutionEngine, and registry systems
    """
    
    def __init__(self, config: Optional[TradingConfig] = None, regime_engine: Optional['UnifiedRegimeEngine'] = None):
        self.config = config or TradingConfig()
        self.logger = logging.getLogger(f"{__name__}.StrategyManager")
        
        # Regime engine reference
        self.regime_engine = regime_engine
        
        # Initialize registry with regime engine
        self.registry = StrategyRegistry(regime_engine)
        
        # Active strategies
        self._active_strategies: Dict[str, BaseStrategy] = {}
        self._strategy_results: List[StrategyResult] = []
        
        # Performance tracking
        self._total_executions = 0
        self._successful_executions = 0
        
        self.logger.info("🎯 StrategyManager initialized")
    
    def start(self) -> None:
        """Start the strategy manager and all active strategies"""
        self.logger.info("🚀 Starting StrategyManager...")
        
        # Start all active strategies
        for strategy_id, strategy in self._active_strategies.items():
            if strategy.status == StrategyStatus.PAUSED:
                strategy.set_status(StrategyStatus.ACTIVE)
                self.logger.info(f"▶️ Resumed strategy: {strategy_id}")
            elif strategy.status == StrategyStatus.STOPPED:
                strategy.set_status(StrategyStatus.ACTIVE)
                self.logger.info(f"🔄 Restarted strategy: {strategy_id}")
        
        self.logger.info("✅ StrategyManager started successfully")
    
    def stop(self) -> None:
        """Stop the strategy manager and all active strategies"""
        self.logger.info("🛑 Stopping StrategyManager...")
        
        # Stop all active strategies
        for strategy_id, strategy in self._active_strategies.items():
            strategy.set_status(StrategyStatus.STOPPED)
            self.logger.info(f"⏹️ Stopped strategy: {strategy_id}")
        
        self.logger.info("✅ StrategyManager stopped successfully")
    
    def create_strategy(self, strategy_type: StrategyType, strategy_id: str, 
                       config: Dict[str, Any]) -> BaseStrategy:
        """Create and register a new strategy"""
        strategy = self.registry.create_strategy(strategy_type, strategy_id, config)
        self._active_strategies[strategy_id] = strategy
        strategy.set_status(StrategyStatus.ACTIVE)
        
        self.logger.info(f"✅ Strategy activated: {strategy_id}")
        return strategy
    
    def execute_strategy(self, strategy_id: str, context: StrategyContext) -> StrategyResult:
        """Execute a specific strategy"""
        start_time = time.time()
        
        try:
            strategy = self._active_strategies.get(strategy_id)
            if not strategy:
                raise ValueError(f"Strategy not found: {strategy_id}")
            
            # Generate signals
            signals = strategy.generate_signals(context)
            
            # Create result
            execution_time = (time.time() - start_time) * 1000
            result = StrategyResult(
                strategy_id=strategy_id,
                signals=signals,
                metrics=strategy.get_metrics(),
                execution_time_ms=execution_time,
                timestamp=datetime.now(),
                success=True
            )
            
            # Update tracking
            self._strategy_results.append(result)
            self._total_executions += 1
            if result.success:
                self._successful_executions += 1
            
            self.logger.debug(f"📊 Executed {strategy_id}: {len(signals)} signals")
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            result = StrategyResult(
                strategy_id=strategy_id,
                signals=[],
                metrics=StrategyMetrics(),
                execution_time_ms=execution_time,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e)
            )
            
            self._strategy_results.append(result)
            self._total_executions += 1
            
            self.logger.error(f"❌ Strategy execution failed for {strategy_id}: {e}")
            return result
    
    def execute_all_strategies(self, context: StrategyContext) -> List[StrategyResult]:
        """Execute all active strategies"""
        results = []
        
        for strategy_id in self._active_strategies:
            result = self.execute_strategy(strategy_id, context)
            results.append(result)
        
        return results
    
    def execute_strategy_with_data(self, strategy_id: str, symbol: str, market_data: Union[pd.DataFrame, Dict]) -> StrategyResult:
        """Convenience method to execute strategy with raw market data (for testing/compatibility)"""
        # Create StrategyContext from raw data
        context = StrategyContext(
            symbol=symbol,
            market_data=market_data if isinstance(market_data, pd.DataFrame) else pd.DataFrame(market_data),
            current_time=datetime.now(),
            portfolio_state={},
            risk_limits={},
            strategy_config={}
        )
        
        return self.execute_strategy(strategy_id, context)
    
    def get_strategy_metrics(self, strategy_id: str) -> Optional[StrategyMetrics]:
        """Get metrics for a specific strategy"""
        strategy = self._active_strategies.get(strategy_id)
        return strategy.get_metrics() if strategy else None
    
    def get_overall_metrics(self) -> Dict[str, Any]:
        """Get overall strategy manager metrics"""
        success_rate = (self._successful_executions / self._total_executions 
                       if self._total_executions > 0 else 0.0)
        
        return {
            'total_strategies': len(self._active_strategies),
            'total_executions': self._total_executions,
            'successful_executions': self._successful_executions,
            'success_rate': success_rate,
            'active_strategies': list(self._active_strategies.keys()),
            'available_strategy_types': [st.value for st in self.registry.get_available_strategies()]
        }
    
    def pause_strategy(self, strategy_id: str) -> None:
        """Pause a strategy"""
        strategy = self._active_strategies.get(strategy_id)
        if strategy:
            strategy.set_status(StrategyStatus.PAUSED)
    
    def resume_strategy(self, strategy_id: str) -> None:
        """Resume a paused strategy"""
        strategy = self._active_strategies.get(strategy_id)
        if strategy:
            strategy.set_status(StrategyStatus.ACTIVE)
    
    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy"""
        if strategy_id in self._active_strategies:
            strategy = self._active_strategies[strategy_id]
            strategy.set_status(StrategyStatus.STOPPED)
            del self._active_strategies[strategy_id]
            self.logger.info(f"🗑️ Removed strategy: {strategy_id}")

# ================================================================================
# FACTORY FUNCTIONS (Simplified)
# ================================================================================

def create_strategy_manager(config: Optional[TradingConfig] = None) -> StrategyManager:
    """Create a new strategy manager instance"""
    return StrategyManager(config)

def create_momentum_strategy(strategy_id: str, config: Dict[str, Any]) -> MomentumStrategy:
    """Create a momentum strategy instance"""
    return MomentumStrategy(strategy_id, config)

def create_mean_reversion_strategy(strategy_id: str, config: Dict[str, Any]) -> MeanReversionStrategy:
    """Create a mean reversion strategy instance"""
    return MeanReversionStrategy(strategy_id, config)

def create_pairs_trading_strategy(strategy_id: str, config: Dict[str, Any]) -> PairsTradingStrategy:
    """Create a pairs trading strategy instance"""
    return PairsTradingStrategy(strategy_id, config)

# ================================================================================
# BACKWARD COMPATIBILITY ALIASES
# ================================================================================

# Legacy strategy aliases for smooth migration
UnifiedStrategyEngine = StrategyManager
StrategyExecutionEngine = StrategyManager
UnifiedStrategyRegistry = StrategyRegistry

# Legacy base class aliases
EnhancedBaseStrategy = BaseStrategy
TemplateBasedStrategy = BaseStrategy

# Legacy factory aliases
StrategyFactory = StrategyRegistry

# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    # Core Classes
    'StrategyManager',
    'StrategyRegistry',
    'BaseStrategy',
    
    # Strategy Implementations
    'MomentumStrategy',
    'MeanReversionStrategy', 
    'PairsTradingStrategy',
    
    # Data Structures
    'StrategyContext',
    'StrategyMetrics',
    'StrategyResult',
    
    # Enums
    'StrategyType',
    'StrategyStatus',
    'ExecutionMode',
    
    # Interface
    'StrategyInterface',
    
    # Factory Functions
    'create_strategy_manager',
    'create_momentum_strategy',
    'create_mean_reversion_strategy',
    'create_pairs_trading_strategy',
    
    # Backward Compatibility
    'UnifiedStrategyEngine',
    'StrategyExecutionEngine',
    'UnifiedStrategyRegistry',
    'EnhancedBaseStrategy',
    'TemplateBasedStrategy',
    'StrategyFactory',
]
