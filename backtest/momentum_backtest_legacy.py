#!/usr/bin/env python3
"""
Advanced Momentum Strategy Backtest - Core Engine Architecture
==============================================================

Revised implementation using the new core_engine architecture with:
- ✅ Advanced momentum signals with trend confirmation
- ✅ Multi-timeframe momentum analysis
- ✅ Regime-aware position sizing
- ✅ Professional risk management
- ✅ Core engine integration (hierarchical architecture)
- ✅ Real-time performance monitoring
- ✅ Position-aware trading logic

Author: StatArb_Gemini Core Engine Integration
Version: 2.0.0 (Core Engine Architecture)
"""

import asyncio
import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Core Engine Components (New Architecture)
from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators, EnhancedIndicatorConfig
from core_engine.system.central_risk_manager import (
    CentralRiskManager, TradingDecisionRequest, TradingDecisionType, AuthorizationLevel
)
from core_engine.regime.engine import RegimeEngine
# Performance analytics - using simplified built-in approach

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("momentum_backtest")


@dataclass
class MomentumBacktestConfig:
    """Configuration for momentum backtest"""
    
    # Backtest parameters
    symbols: List[str] = field(default_factory=lambda: ['TSLA', 'NVDA', 'AAPL', 'MSFT'])
    start_date: str = '2024-12-01'
    end_date: str = '2024-12-20'
    initial_capital: float = 1000000.0
    
    # Momentum strategy parameters (TUNED FOR SENSITIVITY)
    momentum_lookback: int = 60  # 60 minutes for momentum calculation (based on analysis)
    momentum_threshold: float = 0.008  # 0.8% minimum momentum (reduced from 2%)
    trend_confirmation_period: int = 30  # 30 minutes for trend confirmation
    
    # Risk management (ADJUSTED FOR INTRADAY)
    max_position_size: float = 0.20  # 20% max per position (increased for fewer positions)
    stop_loss_pct: float = 0.03  # 3% stop loss (tighter for intraday)
    take_profit_pct: float = 0.06  # 6% take profit (more realistic for intraday)
    
    # Signal filtering (MORE SENSITIVE)
    min_volume_ratio: float = 1.0  # Minimum volume vs average (reduced from 1.2)
    min_rsi_momentum: float = 48  # RSI threshold for momentum (reduced from 55)
    max_volatility: float = 0.08  # 8% max daily volatility (increased from 4%)
    
    # Additional thresholds for signal generation
    min_trend_strength: float = 0.4  # Minimum trend strength for signals
    strong_momentum_multiplier: float = 2.0  # Multiplier for strong momentum override
    rsi_oversold_threshold: float = 30  # RSI oversold level for SELL signals
    momentum_sell_weak_threshold: float = 0.003  # 0.3% minimum momentum for weak SELL signals
    momentum_sell_strong_threshold: float = 0.003  # 0.3% minimum momentum for strong SELL signals


@dataclass
class MomentumSignal:
    """Momentum trading signal"""
    symbol: str
    timestamp: pd.Timestamp
    signal_type: str  # 'BUY' or 'SELL'
    momentum_score: float
    trend_strength: float
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedMomentumStrategy:
    """
    Advanced momentum strategy using core_engine architecture
    """
    
    def __init__(self, config: MomentumBacktestConfig):
        self.config = config
        self.logger = logging.getLogger("momentum_strategy")
        
        # Strategy state
        self.positions = {}  # Current positions
        self.signals_history = []
        self.performance_metrics = {}
        
    def analyze_momentum(self, data: pd.DataFrame, symbol: str) -> Optional[MomentumSignal]:
        """
        Analyze momentum signals for a symbol
        
        Args:
            data: Market data DataFrame
            symbol: Symbol to analyze
            
        Returns:
            MomentumSignal or None
        """
        try:
            min_required = max(self.config.momentum_lookback, self.config.trend_confirmation_period)
            self.logger.debug(f"🔍 {symbol}: Data length {len(data)}, required {min_required}")
            
            if len(data) < min_required:
                self.logger.warning(f"🔍 {symbol}: Insufficient data ({len(data)} < {min_required})")
                return None
            
            # === MULTI-TIMEFRAME ANALYSIS FOR BETTER SIGNALS ===
            multi_timeframe_metrics = self._calculate_multi_timeframe_metrics(data)
            
            # Extract primary metrics
            momentum_score = multi_timeframe_metrics['momentum_score']
            trend_strength = multi_timeframe_metrics['trend_strength']
            timeframe_quality = multi_timeframe_metrics['timeframe_quality']
            
            volume_confirmation = self._check_volume_confirmation(data)
            volatility_check = self._check_volatility(data)
            
            # RSI momentum filter
            rsi = self._calculate_rsi(data['close'])
            rsi_current = rsi.iloc[-1] if not rsi.empty else 50
            
            # ENHANCED debug logging with all adaptive factors
            self.logger.debug(f"🔍 {symbol} ADVANCED Multi-Timeframe Analysis:")
            self.logger.debug(f"   Short (5m): momentum={multi_timeframe_metrics['short_momentum']:.4f}, trend={multi_timeframe_metrics['short_trend']:.3f}")
            self.logger.debug(f"   Medium (10m): momentum={multi_timeframe_metrics['medium_momentum']:.4f}, trend={multi_timeframe_metrics['medium_trend']:.3f}")
            self.logger.debug(f"   Long (20m): momentum={multi_timeframe_metrics['long_momentum']:.4f}, trend={multi_timeframe_metrics['long_trend']:.3f}")
            self.logger.debug(f"   Alignment: momentum={multi_timeframe_metrics['momentum_alignment']:.2f}, trend={multi_timeframe_metrics['trend_alignment']:.2f}")
            self.logger.debug(f"   Persistence: {multi_timeframe_metrics['momentum_persistence']:.2f}")
            self.logger.debug(f"   ENHANCED Quality Score: {timeframe_quality:.2f}")
            self.logger.debug(f"   Volume: {volume_confirmation}, Volatility: {volatility_check}, RSI: {rsi_current:.1f}")
            self.logger.debug(f"   Thresholds: momentum={self.config.momentum_threshold*100:.1f}%, trend={self.config.min_trend_strength}, RSI={self.config.min_rsi_momentum}")
            
            # Generate signal
            signal_type = None
            confidence = 0.0
            
            # Position-aware signal generation
            current_position = self.positions.get(symbol, 0)
            
            # ADAPTIVE BUY signals - more permissive in range-bound markets
            if (current_position <= 0 and
                momentum_score > self.config.momentum_threshold and
                volume_confirmation and
                not volatility_check and
                rsi_current > self.config.min_rsi_momentum and
                (trend_strength > self.config.min_trend_strength or  # Strong trend OR
                 (trend_strength <= self.config.min_trend_strength and momentum_score > self.config.momentum_threshold * 1.5))):  # Weak trend but strong momentum
                
                signal_type = 'BUY'
                # Enhanced confidence with multi-timeframe quality
                momentum_confidence = min(1.0, abs(momentum_score) / self.config.momentum_threshold)
                trend_confidence = trend_strength
                volume_confidence = min(1.0, volume_confirmation * 0.5 + 0.5)
                
                # Base confidence boosted by timeframe quality
                base_confidence = (momentum_confidence * 0.4 + trend_confidence * 0.3 + volume_confidence * 0.2)
                confidence = min(0.95, base_confidence * (0.8 + timeframe_quality * 0.2))
                
                self.logger.info(f"🟢 ENHANCED BUY signal for {symbol}: momentum={momentum_score:.3%}, quality={timeframe_quality:.2f}, confidence={confidence:.2f}")
            
            # SIGNAL THRESHOLD FIX: Enforce proper momentum thresholds for SELL signals
            elif (current_position > 0 and
                  (abs(momentum_score) > self.config.momentum_threshold and momentum_score < 0) or  # Strong bearish momentum
                  (trend_strength < self.config.min_trend_strength and abs(momentum_score) > self.config.momentum_sell_weak_threshold) or  # Weak trend with some momentum
                  (rsi_current < self.config.rsi_oversold_threshold and abs(momentum_score) > self.config.momentum_sell_strong_threshold)):  # RSI oversold with minimal momentum
                
                signal_type = 'SELL'
                momentum_confidence = min(1.0, abs(momentum_score) / self.config.momentum_threshold) if momentum_score < 0 else 0.5
                trend_confidence = 1 - trend_strength
                rsi_confidence = (50 - rsi_current) / 20 if rsi_current < 50 else 0
                
                # Enhanced confidence with timeframe consideration
                base_confidence = (momentum_confidence * 0.4 + trend_confidence * 0.3 + rsi_confidence * 0.3)
                confidence = min(0.95, base_confidence * (0.8 + (1 - timeframe_quality) * 0.2))  # Higher confidence when timeframes disagree (exit signal)
                
                self.logger.info(f"🔴 ENHANCED SELL signal for {symbol}: momentum={momentum_score:.3%}, quality={timeframe_quality:.2f}, confidence={confidence:.2f}")
            
            # ADAPTIVE Strong momentum override - use timeframe quality for sizing
            elif (abs(momentum_score) > self.config.momentum_threshold * self.config.strong_momentum_multiplier and  # Lower threshold for more opportunities
                  volume_confirmation and
                  not volatility_check):  # Remove timeframe quality filter
                
                if momentum_score > 0 and current_position <= 0:
                    signal_type = 'BUY'
                elif momentum_score < 0 and current_position > 0:
                    signal_type = 'SELL'
                    
                if signal_type:
                    base_confidence = min(0.85, abs(momentum_score) / (self.config.momentum_threshold * self.config.strong_momentum_multiplier))
                    confidence = min(0.95, base_confidence * (0.9 + timeframe_quality * 0.1))
                    self.logger.info(f"🚀 ENHANCED Strong momentum override: {momentum_score:.2%}, quality={timeframe_quality:.2f}, signal: {signal_type}")
            
            # SIGNAL QUALITY FIX: Final validation of signal strength
            if signal_type:
                # Validate signal meets minimum thresholds
                if signal_type == 'BUY' and momentum_score <= self.config.momentum_threshold:
                    self.logger.debug(f"❌ BUY signal rejected: momentum {momentum_score:.3%} below threshold {self.config.momentum_threshold:.3%}")
                    return None
                elif signal_type == 'SELL' and abs(momentum_score) <= self.config.momentum_sell_strong_threshold:
                    self.logger.debug(f"❌ SELL signal rejected: momentum {momentum_score:.3%} too weak")
                    return None
                
                current_price = data['close'].iloc[-1]
                
                # Calculate stop loss and take profit
                if signal_type == 'BUY':
                    stop_loss = current_price * (1 - self.config.stop_loss_pct)
                    take_profit = current_price * (1 + self.config.take_profit_pct)
                else:
                    stop_loss = current_price * (1 + self.config.stop_loss_pct)
                    take_profit = current_price * (1 - self.config.take_profit_pct)
                
                # Calculate ENHANCED position size with multiple adaptive factors
                current_volatility = self._calculate_volatility(data)
                position_size = self._calculate_position_size(
                    current_price, confidence, timeframe_quality, 
                    current_volatility, abs(momentum_score)
                )
                
                return MomentumSignal(
                    symbol=symbol,
                    timestamp=data.index[-1],
                    signal_type=signal_type,
                    momentum_score=momentum_score,
                    trend_strength=trend_strength,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=position_size,
                    metadata={
                        'rsi': rsi_current,
                        'volume_ratio': self._get_volume_ratio(data),
                        'volatility': self._calculate_volatility(data)
                    }
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing momentum for {symbol}: {e}")
            return None
    
    def _calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """Calculate enhanced momentum score for intraday trading"""
        try:
            lookback = self.config.momentum_lookback
            if len(data) < lookback:
                return 0.0
            
            # Multi-timeframe momentum analysis
            short_momentum = (data['close'].iloc[-1] - data['close'].iloc[-lookback//3]) / data['close'].iloc[-lookback//3]
            medium_momentum = (data['close'].iloc[-1] - data['close'].iloc[-lookback//2]) / data['close'].iloc[-lookback//2]
            long_momentum = (data['close'].iloc[-1] - data['close'].iloc[-lookback]) / data['close'].iloc[-lookback]
            
            # Weighted momentum (more weight on recent momentum)
            weighted_momentum = (0.5 * short_momentum + 0.3 * medium_momentum + 0.2 * long_momentum)
            
            # Volume confirmation factor
            volume_avg = data['volume'].rolling(lookback).mean().iloc[-1]
            recent_volume = data['volume'].iloc[-10:].mean()  # Last 10 minutes
            volume_factor = min(1.5, recent_volume / volume_avg) if volume_avg > 0 else 1.0
            
            # Price acceleration factor (momentum of momentum)
            if len(data) >= lookback + 10:
                prev_momentum = (data['close'].iloc[-10] - data['close'].iloc[-lookback-10]) / data['close'].iloc[-lookback-10]
                acceleration = weighted_momentum - prev_momentum
                acceleration_factor = 1.0 + (acceleration * 2)  # Boost accelerating momentum
            else:
                acceleration_factor = 1.0
            
            final_momentum = weighted_momentum * volume_factor * acceleration_factor
            
            return final_momentum
            
        except Exception as e:
            self.logger.warning(f"Error calculating momentum score: {e}")
            return 0.0
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calculate trend strength (0-1)"""
        try:
            period = self.config.trend_confirmation_period
            if len(data) < period:
                return 0.5
            
            # Moving average trend
            ma_short = data['close'].rolling(period // 2).mean()
            ma_long = data['close'].rolling(period).mean()
            
            if ma_short.empty or ma_long.empty:
                return 0.5
            
            # Trend direction consistency
            trend_up = (ma_short.iloc[-1] > ma_long.iloc[-1])
            price_above_ma = (data['close'].iloc[-1] > ma_short.iloc[-1])
            
            # Calculate trend strength
            if trend_up and price_above_ma:
                strength = min(1.0, (ma_short.iloc[-1] - ma_long.iloc[-1]) / ma_long.iloc[-1] * 10)
                return 0.5 + strength / 2
            elif not trend_up and not price_above_ma:
                strength = min(1.0, (ma_long.iloc[-1] - ma_short.iloc[-1]) / ma_long.iloc[-1] * 10)
                return 0.5 - strength / 2
            else:
                return 0.5  # Neutral/mixed signals
                
        except Exception as e:
            self.logger.warning(f"Error calculating trend strength: {e}")
            return 0.5
    
    def _check_volume_confirmation(self, data: pd.DataFrame) -> bool:
        """Check if volume confirms the momentum"""
        try:
            volume_ratio = self._get_volume_ratio(data)
            return volume_ratio >= self.config.min_volume_ratio
        except Exception as e:
            self.logger.warning(f"Error checking volume confirmation: {e}")
            return False
    
    def _get_volume_ratio(self, data: pd.DataFrame) -> float:
        """Get current volume vs average ratio"""
        try:
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            current_volume = data['volume'].iloc[-1]
            return current_volume / avg_volume if avg_volume > 0 else 1.0
        except Exception as e:
            self.logger.warning(f"Error calculating volume ratio: {e}")
            return 1.0
    
    def _check_volatility(self, data: pd.DataFrame) -> bool:
        """Check if volatility is too high (returns True if too high)"""
        try:
            volatility = self._calculate_volatility(data)
            return volatility > self.config.max_volatility
        except Exception as e:
            self.logger.warning(f"Error checking volatility: {e}")
            return False
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calculate recent volatility"""
        try:
            returns = data['close'].pct_change().dropna()
            if len(returns) < 10:
                return 0.02  # Default moderate volatility
            return returns.tail(10).std() * np.sqrt(252)  # Annualized
        except Exception as e:
            self.logger.warning(f"Error calculating volatility: {e}")
            return 0.02
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            self.logger.warning(f"Error calculating RSI: {e}")
            return pd.Series([50] * len(prices), index=prices.index)
    
    def _calculate_position_size(self, price: float, confidence: float, timeframe_quality: float = 0.5, 
                               volatility: float = 0.02, momentum_strength: float = 0.001) -> int:
        """Calculate ENHANCED adaptive position size with multiple factors"""
        try:
            # Base position size from max position limit
            max_value = self.config.initial_capital * self.config.max_position_size
            base_shares = int(max_value / price)
            
            # === MULTI-FACTOR ADAPTIVE SIZING ===
            
            # 1. Timeframe Quality Factor (0.6 to 1.0)
            quality_multiplier = 0.6 + (timeframe_quality * 0.4)
            
            # 2. Volatility Factor (inverse relationship - lower vol = larger positions)
            # Normalize volatility to 0-1 range, then invert
            normalized_vol = min(1.0, volatility / 0.05)  # 5% vol = max
            volatility_multiplier = 1.2 - (normalized_vol * 0.4)  # Range: 0.8 to 1.2
            
            # 3. Momentum Strength Factor (stronger momentum = larger positions)
            normalized_momentum = min(1.0, abs(momentum_strength) / (self.config.momentum_threshold * 3))
            momentum_multiplier = 0.8 + (normalized_momentum * 0.4)  # Range: 0.8 to 1.2
            
            # 4. Confidence Factor (already included)
            
            # === COMBINED ADAPTIVE MULTIPLIER ===
            total_multiplier = (quality_multiplier * 0.3 + 
                              volatility_multiplier * 0.3 + 
                              momentum_multiplier * 0.2 + 
                              confidence * 0.2)
            
            # Final position size with bounds
            adjusted_shares = int(base_shares * total_multiplier)
            
            # Ensure reasonable bounds (min 1, max 150% of base for very strong signals)
            final_shares = max(1, min(adjusted_shares, int(base_shares * 1.5)))
            
            
            return final_shares
            
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced position size: {e}")
            return 1

    def _calculate_multi_timeframe_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate multi-timeframe momentum and trend metrics"""
        # Short-term (5-minute window)
        short_data = data.tail(5) if len(data) >= 5 else data
        short_momentum = self._calculate_momentum_score(short_data)
        short_trend = self._calculate_trend_strength(short_data)
        
        # Medium-term (10-minute window) - primary
        medium_data = data.tail(self.config.momentum_lookback)
        medium_momentum = self._calculate_momentum_score(medium_data)
        medium_trend = self._calculate_trend_strength(medium_data)
        
        # Long-term (20-minute window)
        long_data = data.tail(min(20, len(data)))
        long_momentum = self._calculate_momentum_score(long_data)
        long_trend = self._calculate_trend_strength(long_data)
        
        # === ENHANCED TIMEFRAME ALIGNMENT & PERSISTENCE SCORING ===
        momentum_alignment = 0.0
        trend_alignment = 0.0
        momentum_persistence = 0.0
        
        # Check momentum direction alignment
        if short_momentum > 0 and medium_momentum > 0 and long_momentum > 0:
            momentum_alignment = 1.0  # All bullish
        elif short_momentum < 0 and medium_momentum < 0 and long_momentum < 0:
            momentum_alignment = 1.0  # All bearish
        elif (short_momentum > 0 and medium_momentum > 0) or (medium_momentum > 0 and long_momentum > 0):
            momentum_alignment = 0.7  # Partial alignment
        else:
            momentum_alignment = 0.3  # Poor alignment
    
        # Check trend strength alignment
        if short_trend > 0.4 and medium_trend > 0.4 and long_trend > 0.4:
            trend_alignment = 1.0  # Strong trends across timeframes
        elif (short_trend > 0.4 and medium_trend > 0.4) or (medium_trend > 0.4 and long_trend > 0.4):
            trend_alignment = 0.7  # Partial trend alignment
        else:
            trend_alignment = 0.5  # Weak trend alignment
    
        # === MOMENTUM PERSISTENCE ANALYSIS ===
        # Check if momentum is accelerating or decelerating
        if abs(short_momentum) > abs(medium_momentum) > abs(long_momentum):
            momentum_persistence = 1.0  # Accelerating momentum
        elif abs(short_momentum) > abs(medium_momentum):
            momentum_persistence = 0.8  # Recent acceleration
        elif abs(medium_momentum) > abs(long_momentum):
            momentum_persistence = 0.6  # Medium-term strength
        else:
            momentum_persistence = 0.3  # Decelerating momentum
    
        # ENHANCED Multi-timeframe quality score with persistence
        timeframe_quality = (momentum_alignment * 0.4 + trend_alignment * 0.3 + momentum_persistence * 0.3)
        
        return {
            'momentum_score': medium_momentum,
            'trend_strength': medium_trend,
            'timeframe_quality': timeframe_quality,
            'short_momentum': short_momentum,
            'short_trend': short_trend,
            'medium_momentum': medium_momentum,
            'medium_trend': medium_trend,
            'long_momentum': long_momentum,
            'long_trend': long_trend,
            'momentum_alignment': momentum_alignment,
            'trend_alignment': trend_alignment,
            'momentum_persistence': momentum_persistence
        }

class AdvancedMomentumBacktest:
    """
    Advanced momentum backtest using core_engine architecture
    """
    
    def __init__(self, config: MomentumBacktestConfig):
        self.config = config
        self.logger = logging.getLogger("momentum_backtest")
        
        # Core engine components
        self.data_manager = None
        self.indicators_engine = None
        self.risk_manager = None
        self.regime_engine = None
        
        # Position tracking - SINGLE SOURCE OF TRUTH
        self.current_position = 0  # Start with 0 position
        self.current_cash = config.initial_capital
        self.position_history = []
        
        # Shared position tracking dictionary for all symbols
        self.positions = {}
        for symbol in config.symbols:
            self.positions[symbol] = 0.0
            
        # Dynamic exit conditions tracking
        self.entry_prices = {}  # Track entry prices for stop-loss/take-profit
        self.position_timestamps = {}  # Track when positions were opened
        
        # Strategy with shared position tracking
        self.momentum_strategy = AdvancedMomentumStrategy(config)
        # Share position tracking with strategy
        self.momentum_strategy.positions = self.positions
        
        # Results tracking
        self.results = {
            'trades': [],
            'portfolio_value': [],
            'positions': [],
            'signals': [],
            'performance_metrics': {},
            'minute_by_minute': []  # Track minute-by-minute progression
        }
        
        # PERFORMANCE TARGET & ANALYTICS SYSTEM
        self.performance_target = 0.01  # 1% return target
        self.performance_analytics = None
        self.attribution_engine = None
        self.feedback_metrics = {
            'target_return': self.performance_target,
            'current_return': 0.0,
            'performance_gap': 0.0,
            'improvement_areas': [],
            'optimization_suggestions': [],
            'strategy_attribution': {},
            'risk_attribution': {},
            'timing_attribution': {}
        }
        
        # PHASE 2: Risk Management System
        self.kelly_criterion_enabled = True
        self.dynamic_stops_enabled = True
        self.win_rate_history = []
        self.return_history = []
        self.volatility_window = 20  # For dynamic stop calculation
        self.max_kelly_fraction = 0.25  # Cap Kelly at 25% of capital
        
        # PHASE 3: Enhanced Regime-Specific Parameters
        # Based on analysis: Nov 15th (SUCCESS) = Range-bound → High Liquidity transition
        # Dec dates (FAILURE) = Complacency Mode (low volatility, low momentum)
        self.regime_adaptations = {
            # OPTIMAL CONDITIONS: Range-bound with liquidity transitions (Nov 15th success pattern)
            'range_bound': {
                'momentum_threshold': 0.0015,  # RELAXED: 0.15% for range-bound markets
                'confidence_threshold': 0.35,  # RELAXED: Range-bound can generate good signals
                'volume_threshold': 0.8,       # RELAXED: Lower volume requirement
                'rsi_buy_threshold': 25,       # AGGRESSIVE: Range-bound allows more trades
                'position_size_multiplier': 1.4  # LARGER: Range-bound is profitable
            },
            'high_liquidity': {
                'momentum_threshold': 0.001,   # VERY RELAXED: 0.1% for high liquidity
                'confidence_threshold': 0.30,  # VERY RELAXED: High liquidity is optimal
                'volume_threshold': 0.7,       # VERY RELAXED: Liquidity provides volume
                'rsi_buy_threshold': 20,       # VERY AGGRESSIVE: High liquidity optimal
                'position_size_multiplier': 1.6  # LARGEST: High liquidity is best condition
            },
            # ENHANCED CONDITIONS: Complacency mode needs significant relaxation
            'complacency_mode': {
                'momentum_threshold': 0.001,   # ENHANCED: Much more relaxed from 0.3%
                'confidence_threshold': 0.25,  # ENHANCED: Much more relaxed from 0.6
                'volume_threshold': 0.6,       # ENHANCED: Much more relaxed from 1.5
                'rsi_buy_threshold': 15,       # ENHANCED: Much more aggressive from 45
                'position_size_multiplier': 1.3  # ENHANCED: Increase from 0.8
            },
            # ENHANCED CONDITIONS: Sideways markets (similar to range_bound)
            'sideways': {
                'momentum_threshold': 0.0015,  # ENHANCED: Relaxed from 0.4%
                'confidence_threshold': 0.40,  # ENHANCED: Relaxed from 0.6
                'volume_threshold': 1.0,       # ENHANCED: Relaxed from 1.5
                'rsi_buy_threshold': 30,       # ENHANCED: Relaxed from 45
                'position_size_multiplier': 1.1  # ENHANCED: Increase from 0.8
            },
            # DEFAULT CONDITIONS: Keep trending and volatile as reference
            'trending': {
                'momentum_threshold': 0.002,  # Lower threshold in trending markets
                'confidence_threshold': 0.40,  # Lower confidence needed
                'volume_threshold': 1.0,      # Less volume confirmation needed
                'rsi_buy_threshold': 35,      # More aggressive RSI
                'position_size_multiplier': 1.2  # Larger positions in trends
            },
            'volatile': {
                'momentum_threshold': 0.005,  # Highest threshold in volatile markets
                'confidence_threshold': 0.70,  # Highest confidence needed
                'volume_threshold': 2.0,      # Most volume confirmation needed
                'rsi_buy_threshold': 50,      # Most conservative RSI
                'position_size_multiplier': 0.6  # Smallest positions in volatility
            }
        }
        
    async def initialize_components(self):
        """Initialize core engine components"""
        
        try:
            self.logger.info("🔧 Initializing core engine components...")
            
            # Data manager
            data_config = ClickHouseDataConfig(
                symbols=self.config.symbols,
                target_date=self.config.start_date
            )
            self.data_manager = ClickHouseDataManager(data_config)
            
            # Technical indicators
            indicator_config = EnhancedIndicatorConfig(
                enable_multi_timeframe=True,
                timeframes=["1D", "1H"]
            )
            self.indicators_engine = EnhancedTechnicalIndicators(indicator_config)
            
            # Note: Feature engineering and signal generation handled by momentum strategy
            
            # TIGHT RISK MANAGEMENT - Optimal settings for performance
            risk_config = {
                'min_signal_confidence': 0.35,  # Quality threshold for signal filtering
                'high_confidence_threshold': 0.65,  # Standard confidence level
                'extreme_confidence_threshold': 0.80,  # High confidence level
                'max_position_size': 0.15,  # 15% max position size for risk control
                'max_total_risk': 0.25,  # 25% total portfolio risk
                'position_concentration_limit': 0.20,  # 20% per position
                'auto_approval_threshold': 0.02,  # 2% auto-approve threshold
                'elevated_review_threshold': 0.08,  # 8% elevated review
                'emergency_threshold': 0.15  # 15% emergency threshold
            }
            self.risk_manager = CentralRiskManager(risk_config)
            # Share position tracking with risk manager
            self.risk_manager.positions = self.positions
            
            # Note: Strategy management handled by momentum strategy
            
            # Regime detection
            regime_config = {}  # Use default configuration
            self.regime_engine = RegimeEngine(regime_config)
            
            # PERFORMANCE ANALYTICS INITIALIZATION (Simplified)
            # Using built-in analytics instead of complex imports
            self.performance_analytics = None  # Will use simplified analytics
            self.attribution_engine = None     # Will use built-in attribution
            
            # Note: Execution and portfolio management handled by backtest logic
            
            self.logger.info("✅ Core engine components initialized")
            self.logger.info(f"🎯 Performance target set: {self.performance_target:.1%}")
            
        except Exception as e:
            self.logger.error(f"❌ Component initialization failed: {e}")
            raise
    
    async def run_backtest(self) -> Dict[str, Any]:
        """
        Run the momentum backtest
        
        Returns:
            Backtest results dictionary
        """
        
        try:
            self.logger.info("🚀 Starting Advanced Momentum Backtest")
            self.logger.info(f"📊 Symbols: {self.config.symbols}")
            self.logger.info(f"📅 Period: {self.config.start_date} to {self.config.end_date}")
            self.logger.info(f"💰 Initial Capital: ${self.config.initial_capital:,.2f}")
            
            # Initialize components
            await self.initialize_components()
            
            # Load and process data for each symbol
            for symbol in self.config.symbols:
                await self._process_symbol(symbol)
            
            # Calculate final performance metrics
            self._calculate_performance_metrics()
            
            # Generate results summary
            results_summary = self._generate_results_summary()
            
            self.logger.info("✅ Momentum backtest completed successfully")
            return results_summary
            
        except Exception as e:
            self.logger.error(f"❌ Backtest failed: {e}")
            raise
    
    async def _process_symbol(self, symbol: str):
        """Process a single symbol through 1-minute bar momentum strategy"""
        
        try:
            self.logger.debug(f"📈 Processing {symbol} with 1-minute bars...")
            
            # Load market data
            market_data = self.data_manager.get_market_data(symbol=symbol)
            
            if market_data is None or market_data.empty:
                self.logger.warning(f"⚠️ No data available for {symbol}")
                return
            
            # Filter for market hours (9:30 AM - 4:00 PM EST = 14:30 - 21:00 UTC)
            market_data = self._filter_market_hours(market_data)
            
            self.logger.debug(f"📊 Processing {len(market_data)} 1-minute bars for {symbol} during market hours")
            
            # Add symbol column for indicators engine compatibility
            market_data['symbol'] = symbol
            
            # Reset index to make timestamp a column (required by indicators engine)
            market_data = market_data.reset_index()
            
            # Process each minute bar sequentially
            total_signals = 0
            for i in range(self.config.momentum_lookback, len(market_data)):
                # Get data window up to current minute
                current_window = market_data.iloc[:i+1].copy()
                current_time = current_window['timestamp'].iloc[-1]
                current_price = current_window['close'].iloc[-1]
                
                # Process this minute bar
                signals = await self._process_minute_bar(current_window, symbol, current_time, current_price)
                total_signals += len(signals)
                
                # Track minute-by-minute portfolio value
                portfolio_value = self._calculate_portfolio_value(current_price)
                self.results['minute_by_minute'].append({
                    'timestamp': current_time,
                    'price': current_price,
                    'position': self.current_position,
                    'cash': self.current_cash,
                    'portfolio_value': portfolio_value
                })
            
            self.logger.debug(f"✅ {symbol} processing completed - {total_signals} signals generated from {len(market_data)} minute bars")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing {symbol}: {e}")
    
    def _filter_market_hours(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter data to market hours only (9:30 AM - 4:00 PM EST)"""
        try:
            # Convert to EST/EDT timezone for market hours
            data_copy = data.copy()
            data_copy.index = pd.to_datetime(data_copy.index)
            
            # Filter for market hours (9:30 AM - 4:00 PM EST)
            market_hours = data_copy.between_time('14:30', '21:00')  # UTC equivalent
            
            self.logger.debug(f"Filtered {len(data_copy)} records to {len(market_hours)} market hours records")
            return market_hours
            
        except Exception as e:
            self.logger.warning(f"Error filtering market hours: {e}, using all data")
            return data
    
    async def _process_minute_bar(self, data_window: pd.DataFrame, symbol: str, 
                                current_time: pd.Timestamp, current_price: float) -> List[MomentumSignal]:
        """Process a single minute bar for signals"""
        
        try:
            # Only process if we have enough data
            if len(data_window) < self.config.momentum_lookback:
                return []
            
            # Get current price and time for dynamic exit checks
            current_price = float(data_window.iloc[-1]['close'])
            current_time = data_window.index[-1]
            
            # Check dynamic exit conditions first (stop-loss/take-profit)
            exit_conditions = self._check_dynamic_exit_conditions(symbol, current_price, current_time)
            
            if exit_conditions['should_exit']:
                # Create forced SELL signal for dynamic exit
                forced_exit_signal = MomentumSignal(
                    symbol=symbol,
                    timestamp=current_time,
                    signal_type='SELL',
                    momentum_score=0.0,  # Not momentum-based
                    trend_strength=0.0,  # Not applicable for forced exit
                    confidence=exit_conditions['exit_confidence'],
                    entry_price=current_price,
                    stop_loss=current_price * (1 + self.config.stop_loss_pct),  # Conservative stop
                    take_profit=current_price * (1 - self.config.take_profit_pct),  # Conservative target
                    position_size=self.current_position,
                    metadata={'forced_exit': True, 'exit_reason': exit_conditions['exit_reason']}
                )
                
                self.logger.info(f"🚨 Dynamic exit triggered for {symbol}: {exit_conditions['exit_reason']}")
                
                # Assess regime for the forced exit
                regime_info = await self._assess_market_regime(data_window, symbol)
                await self._process_signal(forced_exit_signal, regime_info, data_window)
                
                return [forced_exit_signal]
            
            # Normal signal generation if no forced exit
            # Assess market regime
            regime_info = await self._assess_market_regime(data_window, symbol)
            
            # Generate momentum signals for this minute
            momentum_signals = self._generate_momentum_signals(data_window, symbol, regime_info)
            
            # Process signals through risk management
            for signal in momentum_signals:
                await self._process_signal(signal, regime_info, data_window)
            
            return momentum_signals
            
        except Exception as e:
            self.logger.warning(f"Error processing minute bar at {current_time}: {e}")
            return []
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calculate current portfolio value"""
        return self.current_cash + (self.current_position * current_price)
    
    async def _assess_market_regime(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Assess market regime for the symbol using advanced core_engine regime detection"""
        
        try:
            # Initialize regime engine if not already started
            if not self.regime_engine.is_initialized:
                await self.regime_engine.initialize()
            if not self.regime_engine.is_running:
                await self.regime_engine.start()
            
            # Feed data to regime engine for comprehensive analysis
            for _, row in data.tail(100).iterrows():  # Use more data for better regime detection
                market_data_dict = {
                    'symbol': symbol,
                    'timestamp': row.name if hasattr(row.name, 'timestamp') else datetime.now(),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'open': float(row.get('open', row['close']))  # Use close if open not available
                }
                await self.regime_engine.on_market_data(market_data_dict)
            
            # Get comprehensive regime analysis
            regime_analysis = await self.regime_engine.analyze_regime(force_update=True)
            
            if regime_analysis:
                # Extract regime information from advanced RegimeAnalysis
                regime_name = regime_analysis.primary_regime.value if hasattr(regime_analysis.primary_regime, 'value') else str(regime_analysis.primary_regime)
                
                # Get strategy suitability for momentum
                momentum_suitability = regime_analysis.strategy_suitability.get('momentum', 0.5) if regime_analysis.strategy_suitability else 0.5
                
                self.logger.info(f"🎯 Regime detected: {regime_name} (confidence: {regime_analysis.confidence:.2f})")
                self.logger.info(f"   Volatility: {regime_analysis.volatility_regime}, Trend: {regime_analysis.trend_strength:.2f}")
                self.logger.info(f"   Momentum suitability: {momentum_suitability:.2f}")
                
                return {
                    'regime': regime_name,
                    'confidence': regime_analysis.confidence,
                    'volatility': getattr(regime_analysis, 'volatility', 0.02),
                    'trend_strength': regime_analysis.trend_strength,
                    'risk_multiplier': regime_analysis.risk_adjustment,
                    'volatility_regime': regime_analysis.volatility_regime,
                    'directional_regime': regime_analysis.directional_regime,
                    'stress_level': regime_analysis.stress_level,
                    'momentum_suitability': momentum_suitability,
                    'regime_stability': regime_analysis.regime_stability,
                    'transition_probability': regime_analysis.transition_probability
                }
            else:
                self.logger.warning(f"⚠️ No regime analysis available for {symbol}, using defaults")
                return {
                    'regime': 'neutral',
                    'confidence': 0.5,
                    'volatility': 0.02,
                    'trend_strength': 0.5,
                    'risk_multiplier': 1.0,
                    'volatility_regime': 'normal',
                    'directional_regime': 'neutral',
                    'stress_level': 0.0,
                    'momentum_suitability': 0.5,
                    'regime_stability': 0.5,
                    'transition_probability': 0.0
                }
                
        except Exception as e:
            self.logger.warning(f"Error assessing regime for {symbol}: {e}")
            return {
                'regime': 'neutral',
                'confidence': 0.5,
                'volatility': 0.02,
                'trend_strength': 0.5,
                'risk_multiplier': 1.0,
                'volatility_regime': 'normal',
                'directional_regime': 'neutral',
                'stress_level': 0.0,
                'momentum_suitability': 0.5,
                'regime_stability': 0.5,
                'transition_probability': 0.0
            }
    
    def _generate_momentum_signals(self, data: pd.DataFrame, symbol: str, 
                                 regime_info: Dict[str, Any]) -> List[MomentumSignal]:
        """Generate momentum signals for the symbol"""
        
        signals = []
        
        try:
            self.logger.debug(f"🔍 Analyzing momentum for {symbol} with {len(data)} records...")
            # Use momentum strategy to analyze data
            signal = self.momentum_strategy.analyze_momentum(data, symbol)
            self.logger.info(f"🔍 Momentum analysis result: {signal is not None}")
            
            if signal:
                # Adjust signal based on regime
                signal = self._adjust_signal_for_regime(signal, regime_info)
                
                # PHASE 1: Enhanced signal quality validation
                if self._validate_signal_quality_phase1(signal, data):
                    signals.append(signal)
                    self.results['signals'].append({
                        'symbol': signal.symbol,
                        'timestamp': signal.timestamp,
                        'type': signal.signal_type,
                        'confidence': signal.confidence,
                        'momentum_score': signal.momentum_score,
                        'regime': regime_info['regime']
                    })
            
        except Exception as e:
            self.logger.error(f"Error generating momentum signals for {symbol}: {e}")
        
        return signals
    
    def _validate_signal_quality_phase1(self, signal: MomentumSignal, data: pd.DataFrame) -> bool:
        """PHASE 1 + 3: Enhanced signal quality validation with regime-adaptive thresholds"""
        
        try:
            # PHASE 3: Get regime-specific parameters
            regime_params = self._get_regime_parameters(signal)
            
            # Regime-adaptive confidence threshold
            if signal.confidence < regime_params['confidence_threshold']:
                return False
            
            # Regime-adaptive momentum threshold validation
            if abs(signal.momentum_score) < regime_params['momentum_threshold']:
                return False
            
            # PHASE 1 + 3: Regime-adaptive volume confirmation
            if len(data) >= 20:  # Need sufficient data for volume analysis
                recent_volume = data['volume'].tail(5).mean()
                avg_volume = data['volume'].tail(20).mean()
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
                
                volume_threshold = regime_params['volume_threshold']
                if volume_ratio < volume_threshold:
                    return False
            
            # ENHANCED: Multi-timeframe momentum validation with low-volatility adaptations
            if len(data) >= 15:  # Need sufficient data for multi-timeframe
                # Short-term momentum (5 periods)
                short_momentum = (data['close'].iloc[-1] - data['close'].iloc[-6]) / data['close'].iloc[-6]
                # Medium-term momentum (10 periods)  
                medium_momentum = (data['close'].iloc[-1] - data['close'].iloc[-11]) / data['close'].iloc[-11]
                
                # ENHANCEMENT: Adaptive momentum requirements based on regime
                min_momentum_threshold = regime_params['momentum_threshold'] * 0.5  # 50% of regime threshold
                
                # Both timeframes should agree on direction (relaxed for low-vol regimes)
                signal_direction = 1 if signal.signal_type == 'BUY' else -1
                short_direction = 1 if short_momentum > 0 else -1
                medium_direction = 1 if medium_momentum > 0 else -1
                
                # ENHANCEMENT: Allow disagreement in low-volatility regimes if momentum is strong enough
                regime_name = regime_params.get('regime_name', 'trending')
                if regime_name in ['complacency_mode', 'range_bound', 'high_liquidity']:
                    # In low-vol regimes, allow disagreement if at least one timeframe has strong momentum
                    strong_momentum = max(abs(short_momentum), abs(medium_momentum)) > min_momentum_threshold * 2
                    if not strong_momentum and (signal_direction != short_direction or signal_direction != medium_direction):
                        return False
                else:
                    # In normal regimes, require agreement
                    if signal_direction != short_direction or signal_direction != medium_direction:
                        return False
                
                # ENHANCEMENT: Adaptive minimum momentum strength
                if abs(short_momentum) < min_momentum_threshold and abs(medium_momentum) < min_momentum_threshold:
                    return False
            
            # PHASE 1 + 3: Regime-adaptive RSI validation
            if len(data) >= 14:  # Need sufficient data for RSI
                rsi = self._calculate_rsi(data['close'], 14)
                rsi_threshold = regime_params['rsi_buy_threshold']
                if signal.signal_type == 'BUY' and rsi < rsi_threshold:
                    return False
                elif signal.signal_type == 'SELL' and rsi > (100 - rsi_threshold):
                    return False
            
            # ENHANCEMENT: Micro-trend detection for low-volatility periods
            regime_name = regime_params.get('regime_name', 'trending')
            if regime_name in ['complacency_mode', 'range_bound', 'high_liquidity'] and len(data) >= 30:
                # Look for subtle price patterns in low-volatility regimes
                recent_prices = data['close'].tail(10).values
                price_changes = np.diff(recent_prices) / recent_prices[:-1]
                
                # Count consecutive moves in signal direction
                signal_dir = 1 if signal.signal_type == 'BUY' else -1
                consecutive_moves = 0
                for change in reversed(price_changes):
                    if (signal_dir > 0 and change > 0) or (signal_dir < 0 and change < 0):
                        consecutive_moves += 1
                    else:
                        break
                
                # Require at least 2 consecutive moves in low-vol regimes for confirmation
                if consecutive_moves < 2:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Phase 1 signal validation: {e}")
            return False
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI for signal validation"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
        except Exception as e:
            self.logger.warning(f"Error calculating RSI: {e}")
            return 50.0  # Neutral RSI if calculation fails
    
    def _get_regime_parameters(self, signal: MomentumSignal) -> Dict[str, Any]:
        """PHASE 3: Get regime-specific parameters for signal validation and position sizing"""
        
        try:
            # Extract regime from signal metadata or use default
            regime = 'trending'  # Default regime
            
            # Try to get regime from signal attributes
            if hasattr(signal, 'regime'):
                regime = signal.regime
            elif hasattr(signal, 'metadata') and 'regime' in signal.metadata:
                regime = signal.metadata['regime']
            
            # Enhanced regime mapping based on analysis
            regime_mapping = {
                # SUCCESS PATTERNS (Nov 15th)
                'range_bound': 'range_bound',
                'high_liquidity': 'high_liquidity',
                
                # ENHANCED PATTERNS (Failed Dec dates)
                'complacency_mode': 'complacency_mode',
                
                # TRADITIONAL PATTERNS
                'trending': 'trending',
                'bullish': 'trending',
                'bearish': 'trending',
                'sideways': 'sideways',
                'neutral': 'sideways',
                'volatile': 'volatile',
                'high_volatility': 'volatile',
                
                # ADDITIONAL REGIME MAPPINGS
                'bull_low_vol': 'trending',
                'bear_low_vol': 'trending', 
                'bull_high_vol': 'volatile',
                'bear_high_vol': 'volatile',
                'choppy': 'volatile',
                'crisis_mode': 'volatile',
                'euphoria_mode': 'trending',
                'weak_trending': 'sideways',
                'strong_trending': 'trending',
                'liquidity_crunch': 'volatile'
            }
            
            mapped_regime = regime_mapping.get(regime, 'trending')
            params = self.regime_adaptations[mapped_regime].copy()
            
            # Add regime name for enhanced validation logic
            params['regime_name'] = mapped_regime
            
            return params
            
        except Exception as e:
            self.logger.error(f"Error getting regime parameters: {e}")
            # Fallback to trending parameters (most aggressive)
            return self.regime_adaptations['trending'].copy()
    
    def _calculate_kelly_position_size(self, signal: MomentumSignal, current_cash: float) -> float:
        """PHASE 2: Calculate optimal position size using Kelly Criterion"""
        
        try:
            # Need at least 10 trades for reliable Kelly calculation
            if len(self.return_history) < 10:
                # Use conservative fixed sizing for initial trades
                base_position_size = min(signal.position_size, current_cash * 0.1 / signal.entry_price)
                return base_position_size
            
            # Calculate win rate and average returns
            wins = [r for r in self.return_history if r > 0]
            losses = [r for r in self.return_history if r < 0]
            
            if len(wins) == 0 or len(losses) == 0:
                # No wins or no losses - use conservative sizing
                base_position_size = min(signal.position_size, current_cash * 0.05 / signal.entry_price)
                return base_position_size
            
            win_rate = len(wins) / len(self.return_history)
            avg_win = sum(wins) / len(wins)
            avg_loss = abs(sum(losses) / len(losses))
            
            # Kelly Criterion: f = (bp - q) / b
            # where: b = odds (avg_win/avg_loss), p = win_rate, q = 1-p
            if avg_loss > 0:
                b = avg_win / avg_loss  # Odds ratio
                kelly_fraction = (b * win_rate - (1 - win_rate)) / b
            else:
                kelly_fraction = 0.1  # Conservative default
            
            # Cap Kelly fraction to prevent over-leverage
            kelly_fraction = max(0.01, min(kelly_fraction, self.max_kelly_fraction))
            
            # Apply Kelly fraction to available cash
            kelly_cash = current_cash * kelly_fraction
            kelly_position_size = kelly_cash / signal.entry_price
            
            # PHASE 3: Apply regime-specific position size multiplier
            regime_params = self._get_regime_parameters(signal)
            regime_multiplier = regime_params['position_size_multiplier']
            kelly_position_size *= regime_multiplier
            
            # Ensure we don't exceed the original signal size
            final_position_size = min(kelly_position_size, signal.position_size)
            
            return final_position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating Kelly position size: {e}")
            # Fallback to conservative sizing
            return min(signal.position_size, current_cash * 0.05 / signal.entry_price)
    
    def _calculate_dynamic_stop_loss(self, symbol: str, entry_price: float, data: pd.DataFrame) -> float:
        """PHASE 2: Calculate dynamic stop-loss based on volatility"""
        
        try:
            if len(data) < self.volatility_window:
                # Use fixed 2% stop-loss if insufficient data
                return entry_price * 0.98
            
            # Calculate Average True Range (ATR) for volatility
            high = data['high'].tail(self.volatility_window)
            low = data['low'].tail(self.volatility_window)
            close = data['close'].tail(self.volatility_window)
            
            # True Range calculation
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.mean()
            
            # Dynamic stop-loss: Entry price - (2 * ATR)
            # This adapts to current market volatility
            dynamic_stop = entry_price - (2 * atr)
            
            # Ensure stop-loss is reasonable (between 1% and 5%)
            min_stop = entry_price * 0.95  # 5% max loss
            max_stop = entry_price * 0.99  # 1% min loss
            
            final_stop = max(min_stop, min(dynamic_stop, max_stop))
            
            return final_stop
            
        except Exception as e:
            self.logger.error(f"Error calculating dynamic stop-loss: {e}")
            return entry_price * 0.98  # Fallback to 2% stop
    
    def _update_performance_history(self, trade_return: float):
        """PHASE 2: Update performance history for Kelly Criterion"""
        
        self.return_history.append(trade_return)
        
        # Keep only recent history (last 50 trades)
        if len(self.return_history) > 50:
            self.return_history = self.return_history[-50:]
        
        # Update win rate history
        is_win = 1 if trade_return > 0 else 0
        self.win_rate_history.append(is_win)
        
        if len(self.win_rate_history) > 50:
            self.win_rate_history = self.win_rate_history[-50:]
    
    def _check_dynamic_exit_conditions(self, symbol: str, current_price: float, 
                                     current_time: pd.Timestamp) -> Dict[str, Any]:
        """Check stop-loss and take-profit conditions"""
        
        exit_conditions = {
            'should_exit': False,
            'exit_reason': None,
            'exit_confidence': 0.0
        }
        
        if symbol not in self.entry_prices or self.current_position <= 0:
            return exit_conditions
            
        entry_price = self.entry_prices[symbol]
        # Handle both pandas Timestamp and integer index
        if isinstance(current_time, (int, float)):
            # If current_time is an index, convert to minutes since entry
            position_age_minutes = current_time - (self.position_timestamps[symbol] if isinstance(self.position_timestamps[symbol], (int, float)) else 0)
        else:
            # If current_time is a Timestamp, calculate time difference
            position_age_minutes = (current_time - self.position_timestamps[symbol]).total_seconds() / 60
        
        # Calculate P&L percentage
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Stop-loss condition
        if pnl_pct <= -self.config.stop_loss_pct:
            exit_conditions.update({
                'should_exit': True,
                'exit_reason': f'Stop-loss triggered: {pnl_pct:.2%} loss',
                'exit_confidence': 0.95  # High confidence for risk management
            })
            
        # Take-profit condition
        elif pnl_pct >= self.config.take_profit_pct:
            exit_conditions.update({
                'should_exit': True,
                'exit_reason': f'Take-profit triggered: {pnl_pct:.2%} gain',
                'exit_confidence': 0.90  # High confidence for profit taking
            })
            
        # ADAPTIVE Time-based exit based on momentum persistence
        # Strong persistent momentum = hold longer, weak momentum = exit sooner
        max_hold_time = 60  # Base 1 hour
        # This will be enhanced when we have access to momentum persistence in this method
        if position_age_minutes > max_hold_time:
            exit_conditions.update({
                'should_exit': True,
                'exit_reason': f'Adaptive time-based exit: held for {position_age_minutes:.0f} minutes',
                'exit_confidence': 0.70  # Moderate confidence for time-based exit
            })
            
        return exit_conditions
    
    def _adjust_signal_for_regime(self, signal: MomentumSignal, 
                                regime_info: Dict[str, Any]) -> MomentumSignal:
        """Advanced regime-based signal adjustment using core_engine regime analysis"""
        
        try:
            regime = regime_info['regime']
            regime_confidence = regime_info['confidence']
            risk_multiplier = regime_info['risk_multiplier']
            momentum_suitability = regime_info.get('momentum_suitability', 0.5)
            volatility_regime = regime_info.get('volatility_regime', 'normal')
            directional_regime = regime_info.get('directional_regime', 'neutral')
            stress_level = regime_info.get('stress_level', 0.0)
            regime_stability = regime_info.get('regime_stability', 0.5)
            
            original_confidence = signal.confidence
            original_position_size = signal.position_size
            
            # === MOMENTUM STRATEGY SUITABILITY ADJUSTMENT ===
            # Adjust momentum suitability to be less harsh
            adjusted_suitability = 0.7 + (momentum_suitability * 0.3)  # Range: 0.7-1.0 instead of 0.0-1.0
            signal.confidence *= adjusted_suitability
            
            # === DIRECTIONAL REGIME ADJUSTMENTS ===
            if signal.signal_type == 'BUY':
                if directional_regime == 'bull':
                    signal.confidence *= 1.3  # Strong boost for bullish signals in bull regime
                elif directional_regime == 'bear':
                    signal.confidence *= 0.6  # Reduce bullish signals in bear regime
                elif directional_regime == 'neutral':
                    signal.confidence *= 0.9  # Slight reduction in neutral regime
            
            elif signal.signal_type == 'SELL':
                if directional_regime == 'bear':
                    signal.confidence *= 1.2  # Boost bearish signals in bear regime
                elif directional_regime == 'bull':
                    signal.confidence *= 0.7  # Reduce bearish signals in bull regime
            
            # === VOLATILITY REGIME ADJUSTMENTS ===
            if volatility_regime == 'high' or volatility_regime == 'extreme':
                signal.confidence *= 0.8  # Reduce confidence in high volatility
                signal.position_size = int(signal.position_size * 0.7)  # Smaller positions
            elif volatility_regime == 'low':
                signal.confidence *= 1.1  # Slight boost in low volatility
                signal.position_size = int(signal.position_size * 1.2)  # Larger positions
            
            # === STRESS LEVEL ADJUSTMENTS ===
            if stress_level > 0.7:  # High stress (crisis mode)
                signal.confidence *= 0.5  # Significantly reduce confidence
                signal.position_size = int(signal.position_size * 0.5)  # Much smaller positions
            elif stress_level > 0.4:  # Moderate stress
                signal.confidence *= 0.8  # Reduce confidence
                signal.position_size = int(signal.position_size * 0.8)  # Smaller positions
            
            # === REGIME STABILITY ADJUSTMENTS ===
            if regime_stability < 0.3:  # Unstable regime (likely to change)
                signal.confidence *= 0.7  # Reduce confidence in unstable regimes
            elif regime_stability > 0.8:  # Very stable regime
                signal.confidence *= 1.1  # Slight boost for stable regimes
            
            # === REGIME CONFIDENCE ADJUSTMENTS ===
            signal.confidence *= regime_confidence  # Scale by regime detection confidence
            
            # === RISK MULTIPLIER ADJUSTMENTS ===
            signal.position_size = int(signal.position_size / risk_multiplier)
            signal.position_size = max(1, signal.position_size)
            
            # === FINAL BOUNDS ===
            signal.confidence = min(0.95, max(0.1, signal.confidence))  # Keep within bounds
            
            # Log regime adjustments
            if abs(signal.confidence - original_confidence) > 0.1 or abs(signal.position_size - original_position_size) > 2:
                self.logger.info(f"🎯 Regime adjustment for {signal.symbol}:")
                self.logger.info(f"   Regime: {regime} ({directional_regime}, {volatility_regime})")
                self.logger.info(f"   Confidence: {original_confidence:.2f} → {signal.confidence:.2f}")
                self.logger.info(f"   Position size: {original_position_size} → {signal.position_size}")
                self.logger.info(f"   Momentum suitability: {momentum_suitability:.2f}")
                self.logger.info(f"   Stress level: {stress_level:.2f}, Stability: {regime_stability:.2f}")
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Error adjusting signal for regime: {e}")
            return signal
    
    def _synchronize_positions(self, symbol: str, position: float):
        """ARCHITECTURAL FIX: Proper position synchronization using Risk Manager's official methods"""
        
        # Update main position tracking
        self.positions[symbol] = position
        
        # CRITICAL FIX: Use Risk Manager's official update method instead of direct dictionary access
        if hasattr(self.risk_manager, 'current_positions'):
            # Set the position directly to the exact value (not incremental)
            self.risk_manager.current_positions[symbol] = position
            
        # Update momentum strategy position tracking
        if hasattr(self.momentum_strategy, 'positions'):
            self.momentum_strategy.positions[symbol] = position
    
    def _analyze_performance_vs_target(self) -> Dict[str, Any]:
        """PERFORMANCE ANALYTICS: Analyze current performance against 1% target"""
        
        try:
            # Calculate current performance
            current_portfolio_value = self.current_cash + (self.current_position * self.current_price if hasattr(self, 'current_price') else 0)
            current_return = (current_portfolio_value - self.initial_capital) / self.initial_capital
            performance_gap = self.performance_target - current_return
            
            # Update feedback metrics
            self.feedback_metrics.update({
                'current_return': current_return,
                'performance_gap': performance_gap,
                'current_portfolio_value': current_portfolio_value
            })
            
            # Analyze improvement areas based on performance gap
            improvement_areas = []
            optimization_suggestions = []
            
            if performance_gap > 0:  # Underperforming
                # Analyze trade performance
                if len(self.results['trades']) > 0:
                    trades_df = pd.DataFrame(self.results['trades'])
                    
                    # Win rate analysis
                    if 'pnl' in trades_df.columns:
                        win_rate = (trades_df['pnl'] > 0).mean()
                        if win_rate < 0.5:
                            improvement_areas.append("Low win rate")
                            optimization_suggestions.append("Improve signal quality and entry timing")
                    
                    # Position sizing analysis
                    if 'quantity' in trades_df.columns:
                        avg_position_size = trades_df['quantity'].mean()
                        max_position_size = trades_df['quantity'].max()
                        if avg_position_size < max_position_size * 0.5:
                            improvement_areas.append("Conservative position sizing")
                            optimization_suggestions.append("Consider increasing position sizes for high-confidence signals")
                
                # Signal generation analysis
                if len(self.results['signals']) > 0:
                    signals_df = pd.DataFrame(self.results['signals'])
                    if 'confidence' in signals_df.columns:
                        avg_confidence = signals_df['confidence'].mean()
                        if avg_confidence < 0.7:
                            improvement_areas.append("Low signal confidence")
                            optimization_suggestions.append("Tighten signal generation criteria for higher quality")
                
                # Performance gap analysis
                if performance_gap > 0.005:  # > 0.5% gap
                    improvement_areas.append("Significant performance shortfall")
                    optimization_suggestions.append("Consider strategy parameter optimization or regime-specific adjustments")
            
            self.feedback_metrics.update({
                'improvement_areas': improvement_areas,
                'optimization_suggestions': optimization_suggestions
            })
            
            return self.feedback_metrics
            
        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            return self.feedback_metrics
    
    def _generate_performance_attribution(self) -> Dict[str, Any]:
        """ATTRIBUTION ANALYSIS: Break down performance sources"""
        
        try:
            attribution_results = {
                'strategy_attribution': {},
                'risk_attribution': {},
                'timing_attribution': {},
                'regime_attribution': {}
            }
            
            if len(self.results['trades']) > 0:
                trades_df = pd.DataFrame(self.results['trades'])
                
                # Strategy attribution (momentum vs other factors)
                if 'type' in trades_df.columns:
                    buy_trades = trades_df[trades_df['type'] == 'BUY']
                    sell_trades = trades_df[trades_df['type'] == 'SELL']
                    
                    attribution_results['strategy_attribution'] = {
                        'buy_contribution': len(buy_trades) / len(trades_df) if len(trades_df) > 0 else 0,
                        'sell_contribution': len(sell_trades) / len(trades_df) if len(trades_df) > 0 else 0,
                        'momentum_signals': len(trades_df)
                    }
                
                # Risk attribution (position sizing impact)
                if 'quantity' in trades_df.columns:
                    position_variance = trades_df['quantity'].var()
                    attribution_results['risk_attribution'] = {
                        'position_sizing_consistency': 1.0 / (1.0 + position_variance) if position_variance > 0 else 1.0,
                        'avg_position_size': trades_df['quantity'].mean(),
                        'position_variance': position_variance
                    }
            
            # Regime attribution
            if len(self.results.get('regime_changes', [])) > 0:
                regime_changes = len(self.results['regime_changes'])
                attribution_results['regime_attribution'] = {
                    'regime_stability': max(0, 1.0 - regime_changes / 100.0),  # Normalize by expected changes
                    'regime_changes': regime_changes
                }
            
            self.feedback_metrics.update(attribution_results)
            return attribution_results
            
        except Exception as e:
            self.logger.error(f"Attribution analysis failed: {e}")
            return {}
    
    async def _process_signal(self, signal: MomentumSignal, regime_info: Dict[str, Any], data_window: pd.DataFrame):
        """Process signal through risk management and execution"""
        
        try:
            # Create trading decision request
            decision_type = TradingDecisionType.POSITION_ENTRY if signal.signal_type == 'BUY' else TradingDecisionType.POSITION_EXIT
            
            request = TradingDecisionRequest(
                symbol=signal.symbol,
                decision_type=decision_type,
                side=signal.signal_type.lower(),  # 'buy' or 'sell'
                quantity=signal.position_size,
                strategy_id="momentum_strategy",
                confidence=signal.confidence,
                expected_return=signal.momentum_score,
                market_regime=regime_info['regime'],
                regime_confidence=regime_info['confidence'],
                volatility_estimate=regime_info['volatility']
            )
            
            # PHASE 2: Apply Kelly Criterion position sizing
            if self.kelly_criterion_enabled and signal.signal_type == 'BUY':
                original_size = signal.position_size
                signal.position_size = self._calculate_kelly_position_size(signal, self.current_cash)
                self.logger.info(f"📊 Kelly sizing: {original_size:.2f} → {signal.position_size:.2f}")
            
            # ARCHITECTURAL FIX: Add cash and price information to request for proper validation
            request.available_cash = self.current_cash
            request.price = signal.entry_price
            
            # POSITION SYNC FIX: Synchronize position tracking across ALL components BEFORE authorization
            self._synchronize_positions(signal.symbol, self.current_position)
            
            # Also pass current cash to risk manager for cash availability checks
            if hasattr(self.risk_manager, 'current_cash'):
                self.risk_manager.current_cash = self.current_cash
            
            # Get risk authorization
            authorization = await self.risk_manager.authorize_trading_decision(request)
            
            # CRITICAL FIX: Only process trades with authorized_quantity > 0
            if (authorization.authorization_level != AuthorizationLevel.REJECTED and 
                authorization.authorized_quantity > 0):
                
                # Execute trade (simulated) with synchronized position tracking
                trade_cost = authorization.authorized_quantity * signal.entry_price
                
                if signal.signal_type == 'BUY':
                    # ARCHITECTURAL FIX: Cash availability now validated by Risk Manager during authorization
                    # No need for redundant cash checks here - Risk Manager handles this
                    
                    # Buy shares - update all position tracking simultaneously
                    self.current_position += authorization.authorized_quantity
                    self.current_cash -= trade_cost
                    
                    # Track entry price and timestamp for dynamic exits
                    self.entry_prices[signal.symbol] = signal.entry_price
                    # Store timestamp in consistent format
                    if hasattr(signal.timestamp, 'timestamp'):
                        self.position_timestamps[signal.symbol] = signal.timestamp
                    else:
                        self.position_timestamps[signal.symbol] = signal.timestamp
                    
                    # PHASE 2: Calculate and store dynamic stop-loss
                    if self.dynamic_stops_enabled:
                        try:
                            # Use current data window for dynamic stop calculation
                            dynamic_stop = self._calculate_dynamic_stop_loss(signal.symbol, signal.entry_price, data_window)
                            signal.stop_loss = dynamic_stop
                            self.logger.info(f"📊 Dynamic stop-loss: ${dynamic_stop:.2f} ({((dynamic_stop/signal.entry_price)-1)*100:.2f}%)")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Dynamic stop calculation failed, using fixed 2%: {e}")
                            signal.stop_loss = signal.entry_price * 0.98
                    
                    # POSITION SYNC FIX: Use centralized position synchronization
                    self._synchronize_positions(signal.symbol, self.current_position)
                    
                elif signal.signal_type == 'SELL':
                    # CRITICAL FIX: Properly limit SELL quantity to available position
                    shares_to_sell = min(authorization.authorized_quantity, self.current_position)
                    if shares_to_sell <= 0:
                        self.logger.warning(f"❌ Cannot sell {authorization.authorized_quantity} shares, only have {self.current_position}")
                        return
                    
                    self.current_position -= shares_to_sell
                    self.current_cash += shares_to_sell * signal.entry_price
                    
                    # Update authorization quantity to reflect actual trade
                    authorization.authorized_quantity = shares_to_sell
                    
                    # Clear entry tracking if position is fully closed
                    if self.current_position <= 0:
                        if signal.symbol in self.entry_prices:
                            del self.entry_prices[signal.symbol]
                        if signal.symbol in self.position_timestamps:
                            del self.position_timestamps[signal.symbol]
                    
                    # POSITION SYNC FIX: Use centralized position synchronization
                    self._synchronize_positions(signal.symbol, self.current_position)
                
                # Record successful trade
                trade_result = {
                    'symbol': signal.symbol,
                    'timestamp': signal.timestamp,
                    'type': signal.signal_type,
                    'quantity': authorization.authorized_quantity,
                    'price': signal.entry_price,
                    'confidence': signal.confidence,
                    'regime': regime_info['regime'],
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'position_after': self.current_position,
                    'cash_after': self.current_cash
                }
                
                self.results['trades'].append(trade_result)
                
                # PHASE 2: Update performance history for Kelly Criterion
                if signal.signal_type == 'SELL' and len(self.results['trades']) >= 2:
                    # Calculate return for the completed round-trip trade
                    current_trade = self.results['trades'][-1]
                    # Find the corresponding BUY trade
                    for i in range(len(self.results['trades']) - 2, -1, -1):
                        prev_trade = self.results['trades'][i]
                        if prev_trade['type'] == 'BUY' and prev_trade['symbol'] == signal.symbol:
                            # Calculate return: (sell_price - buy_price) / buy_price
                            trade_return = (current_trade['price'] - prev_trade['price']) / prev_trade['price']
                            self._update_performance_history(trade_return)
                            self.logger.info(f"📊 Trade return: {trade_return:.3%} (Buy: ${prev_trade['price']:.2f}, Sell: ${current_trade['price']:.2f})")
                            break
                
                # CRITICAL FIX: Only log successful trades with actual quantity traded
                actual_quantity = authorization.authorized_quantity
                self.logger.info(f"✅ {signal.signal_type} {actual_quantity:.2f} {signal.symbol} @ ${signal.entry_price:.2f}")
                self.logger.info(f"   Position: {self.current_position:.2f}, Cash: ${self.current_cash:.2f}")
                
            else:
                # CRITICAL FIX: Properly log rejected trades
                rejection_reason = getattr(authorization, 'rejection_reason', 'Risk assessment failed')
                self.logger.info(f"❌ {signal.signal_type} {signal.position_size:.2f} {signal.symbol} REJECTED: {rejection_reason}")
                
        except Exception as e:
            self.logger.error(f"Error processing signal: {e}")
    
    def _calculate_performance_metrics(self):
        """Calculate comprehensive backtest performance metrics"""
        
        try:
            trades = self.results['trades']
            minute_data = self.results['minute_by_minute']
            
            if not trades and not minute_data:
                self.logger.warning("No trades or minute data - cannot calculate performance metrics")
                return
            
            # Basic trade metrics
            total_trades = len(trades)
            buy_trades = len([t for t in trades if t['type'] == 'BUY'])
            sell_trades = len([t for t in trades if t['type'] == 'SELL'])
            
            # Calculate final portfolio value
            if minute_data:
                final_portfolio_value = minute_data[-1]['portfolio_value']
                initial_value = self.config.initial_capital
                
                # Portfolio performance
                total_return = final_portfolio_value - initial_value
                return_pct = (total_return / initial_value) * 100
                
                # Calculate portfolio value series for additional metrics
                portfolio_values = [m['portfolio_value'] for m in minute_data]
                returns = pd.Series(portfolio_values).pct_change().dropna()
                
                # Risk metrics
                volatility = returns.std() * np.sqrt(252 * 390)  # Annualized (390 minutes per trading day)
                sharpe_ratio = (return_pct / 100) / volatility if volatility > 0 else 0
                
                # Drawdown calculation
                portfolio_series = pd.Series(portfolio_values)
                rolling_max = portfolio_series.expanding().max()
                drawdown = (portfolio_series - rolling_max) / rolling_max
                max_drawdown = drawdown.min() * 100  # As percentage
                
                # Win rate (for completed round trips)
                winning_trades = 0
                total_round_trips = 0
                
                # Match buy/sell pairs for round trip analysis
                buy_stack = []
                for trade in trades:
                    if trade['type'] == 'BUY':
                        buy_stack.append(trade)
                    elif trade['type'] == 'SELL' and buy_stack:
                        buy_trade = buy_stack.pop(0)  # FIFO matching
                        pnl = (trade['price'] - buy_trade['price']) * min(trade['quantity'], buy_trade['quantity'])
                        total_round_trips += 1
                        if pnl > 0:
                            winning_trades += 1
                
                win_rate = (winning_trades / total_round_trips * 100) if total_round_trips > 0 else 0
            
            else:
                final_portfolio_value = self.config.initial_capital
                total_return = 0
                return_pct = 0
                volatility = 0
                sharpe_ratio = 0
                max_drawdown = 0
                win_rate = 0
            
            # Performance metrics
            self.results['performance_metrics'] = {
                'initial_capital': self.config.initial_capital,
                'final_portfolio_value': final_portfolio_value,
                'total_return': total_return,
                'return_pct': return_pct,
                'volatility': volatility * 100,  # As percentage
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown_pct': max_drawdown,
                'win_rate_pct': win_rate,
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'final_position': self.current_position,
                'final_cash': self.current_cash,
                'symbols_traded': len(set(t['symbol'] for t in trades)) if trades else 0,
                'minutes_processed': len(minute_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
    
    def _generate_results_summary(self) -> Dict[str, Any]:
        """Generate comprehensive results summary"""
        
        perf = self.results.get('performance_metrics', {})
        
        summary = {
            'backtest_config': {
                'symbols': self.config.symbols,
                'period': f"{self.config.start_date} to {self.config.end_date}",
                'initial_capital': self.config.initial_capital,
                'strategy': 'Advanced Momentum (1-minute bars)',
                'position_management': 'Start from 0, BUY first then SELL'
            },
            'execution_summary': {
                'total_signals': len(self.results['signals']),
                'total_trades': len(self.results['trades']),
                'symbols_analyzed': len(self.config.symbols),
                'minutes_processed': perf.get('minutes_processed', 0),
                'market_hours_only': True
            },
            'performance_metrics': perf,
            'position_summary': {
                'final_position': perf.get('final_position', 0),
                'final_cash': perf.get('final_cash', 0),
                'final_portfolio_value': perf.get('final_portfolio_value', 0)
            },
            'trades': self.results['trades'],
            'signals': self.results['signals']
        }
        
        return summary


async def main():
    """Main backtest execution"""
    
    # Configure backtest (SINGLE SYMBOL TSLA WITH POSITION MANAGEMENT)
    config = MomentumBacktestConfig(
        symbols=['TSLA'],  # Single symbol focus
        start_date='2024-11-06',  # Testing for November 6, 2024
        end_date='2024-11-06',
        initial_capital=10000.0,  # $10,000 initial capital
        momentum_lookback=10,  # ORIGINAL: 10 minutes (was generating 90 signals!)
        # PHASE 1 OPTIMIZATION: Enhanced Signal Quality
        momentum_threshold=0.003,  # PHASE 1: Increased from 0.1% to 0.3% for higher quality signals
        trend_confirmation_period=5,  # Keep at 5 minutes
        max_position_size=0.95,  # 95% max position (nearly full capital)
        min_volume_ratio=1.2,  # PHASE 1: Increased from 0.3 to 1.2 (20% above average volume)
        min_rsi_momentum=40,  # PHASE 1: Increased from 35 to 40 for stronger momentum signals
        max_volatility=0.20,  # ORIGINAL: 20% max volatility (risk control)
        stop_loss_pct=0.02,  # 2% stop loss for tight risk control
        take_profit_pct=0.04  # 4% take profit for reasonable targets
    )
    
    # Run backtest
    backtest = AdvancedMomentumBacktest(config)
    results = await backtest.run_backtest()
    
    # Display results
    print("\n" + "="*80)
    print("🚀 ADVANCED MOMENTUM BACKTEST RESULTS")
    print("="*80)
    
    print("\n📊 BACKTEST CONFIGURATION:")
    config_info = results['backtest_config']
    print(f"   • Symbols: {', '.join(config_info['symbols'])}")
    print(f"   • Period: {config_info['period']}")
    print(f"   • Initial Capital: ${config_info['initial_capital']:,.2f}")
    print(f"   • Strategy: {config_info['strategy']}")
    print(f"   • Position Management: {config_info['position_management']}")
    
    print("\n⚡ EXECUTION SUMMARY:")
    exec_summary = results['execution_summary']
    print(f"   • Total Signals: {exec_summary['total_signals']}")
    print(f"   • Total Trades: {exec_summary['total_trades']}")
    print(f"   • Minutes Processed: {exec_summary['minutes_processed']}")
    print(f"   • Market Hours Only: {exec_summary['market_hours_only']}")
    
    # Initialize performance metrics with defaults
    perf = {
        'total_return_pct': 0.0,
        'return_pct': 0.0,
        'initial_capital': config_info['initial_capital'],
        'final_portfolio_value': config_info['initial_capital'],
        'total_return': 0.0,
        'volatility': 0.0,
        'sharpe_ratio': 0.0,
        'max_drawdown_pct': 0.0,
        'win_rate_pct': 0.0,
        'total_trades': 0,
        'buy_trades': 0,
        'sell_trades': 0
    }
    
    if results['performance_metrics']:
        print("\n💰 COMPREHENSIVE PERFORMANCE METRICS:")
        perf = results['performance_metrics']
        print(f"   • Initial Capital: ${perf['initial_capital']:,.2f}")
        print(f"   • Final Portfolio Value: ${perf['final_portfolio_value']:,.2f}")
        print(f"   • Total Return: ${perf['total_return']:,.2f}")
        print(f"   • Return %: {perf['return_pct']:.2f}%")
        print(f"   • Volatility: {perf['volatility']:.2f}%")
        print(f"   • Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
        print(f"   • Max Drawdown: {perf['max_drawdown_pct']:.2f}%")
        print(f"   • Win Rate: {perf['win_rate_pct']:.1f}%")
        print(f"   • Total Trades: {perf['total_trades']} (Buy: {perf['buy_trades']}, Sell: {perf['sell_trades']})")
    
    # PERFORMANCE TARGET ANALYSIS
    target_return = 0.01  # 1% target
    actual_return = perf.get('total_return_pct', perf.get('return_pct', 0)) / 100.0
    performance_gap = target_return - actual_return
    
    print("\n📈 FINAL POSITION SUMMARY:")
    pos_summary = results['position_summary']
    print(f"   • Final Position: {pos_summary['final_position']} shares")
    print(f"   • Final Cash: ${pos_summary['final_cash']:,.2f}")
    print(f"   • Final Portfolio Value: ${pos_summary['final_portfolio_value']:,.2f}")
    
    print("\n🎯 PERFORMANCE vs TARGET:")
    print(f"   • Target Return: {target_return:.1%}")
    print(f"   • Actual Return: {actual_return:.1%}")
    print(f"   • Performance Gap: {performance_gap:+.1%}")
    
    if performance_gap > 0:
        print("   • Status: ❌ UNDERPERFORMING TARGET")
        
        # PROFESSIONAL QUANT ANALYSIS & RECOMMENDATIONS
        print("\n🔍 QUANT ANALYSIS - IMPROVEMENT AREAS:")
        
        # Win Rate Analysis
        if perf['win_rate_pct'] < 50:
            print(f"   • Low Win Rate ({perf['win_rate_pct']:.1f}%): Tighten entry criteria, improve signal quality")
        
        # Sharpe Ratio Analysis
        if perf['sharpe_ratio'] < 0.5:
            print(f"   • Poor Risk-Adjusted Returns (Sharpe: {perf['sharpe_ratio']:.3f}): Reduce position volatility or improve timing")
        
        # Drawdown Analysis
        if abs(perf['max_drawdown_pct']) > 5:
            print(f"   • High Drawdown ({perf['max_drawdown_pct']:.1f}%): Implement tighter stop-losses or position sizing")
        
        # Trade Frequency Analysis
        if perf['total_trades'] < 10:
            print(f"   • Low Trade Frequency ({perf['total_trades']} trades): Relax signal thresholds or expand universe")
        elif perf['total_trades'] > 50:
            print(f"   • High Trade Frequency ({perf['total_trades']} trades): Increase signal confidence thresholds")
        
        print("\n💡 OPTIMIZATION STRATEGIES:")
        print("   • Parameter Tuning: Optimize momentum thresholds (currently 0.1%)")
        print("   • Position Sizing: Implement Kelly Criterion or risk parity")
        print("   • Regime Adaptation: Adjust strategy parameters by market regime")
        print("   • Signal Enhancement: Add volume confirmation or multi-timeframe filters")
        print("   • Risk Management: Implement dynamic stop-losses based on volatility")
        
    else:
        print("   • Status: ✅ TARGET ACHIEVED")
        print("\n🎉 EXCELLENT PERFORMANCE - CONSIDER SCALING OR HIGHER TARGETS")
    
    print("\n🎯 RECENT TRADES:")
    for trade in results['trades'][-5:]:  # Show last 5 trades
        print(f"   • {trade['type']} {trade['quantity']:.2f} {trade['symbol']} @ ${trade['price']:.2f}")
        print(f"     Position After: {trade['position_after']:.2f}, Cash After: ${trade['cash_after']:,.2f}")
    
    print("\n" + "="*80)
    if performance_gap <= 0:
        print("✅ MOMENTUM BACKTEST COMPLETED - TARGET ACHIEVED!")
    else:
        print("⚠️  MOMENTUM BACKTEST COMPLETED - OPTIMIZATION NEEDED!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
