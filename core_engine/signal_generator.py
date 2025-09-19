#!/usr/bin/env python3
"""
Signal Generation Engine for Core Engine
========================================

Generates trading signals from engineered features using multiple strategies:
- Mean reversion signals
- Momentum signals  
- Multi-factor signals
- Machine learning signals

Author: StatArb_Gemini Core Engine
Version: 1.0.0 (Signal Generation)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Types of trading signals"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3

@dataclass
class TradingSignal:
    """Trading signal structure"""
    symbol: str
    timestamp: pd.Timestamp
    signal_type: SignalType
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: float = 0.0  # Suggested position size (0.0 to 1.0)
    strategy: str = "multi_factor"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SignalConfig:
    """Configuration for signal generation"""
    # Strategy weights
    mean_reversion_weight: float = 0.4
    momentum_weight: float = 0.4
    volume_weight: float = 0.2
    
    # Thresholds
    signal_threshold: float = 0.6  # Minimum confidence for signal generation
    strong_signal_threshold: float = 0.8
    
    # Risk parameters
    max_position_size: float = 0.1  # 10% max position
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    
    # Signal filtering
    min_volume_ratio: float = 0.5  # Minimum volume vs average
    max_volatility_percentile: float = 0.95  # Filter extreme volatility
    
    # Machine learning
    enable_ml_signals: bool = True
    ml_confidence_threshold: float = 0.65

class SignalGenerator:
    """
    Multi-Strategy Signal Generator
    
    Combines multiple signal generation strategies:
    1. Mean Reversion: RSI, Bollinger Bands, oversold/overbought conditions
    2. Momentum: MACD, price momentum, trend following
    3. Volume: Volume breakouts, volume-price relationships
    4. Multi-factor: Combination of all signals with ML enhancement
    """
    
    def __init__(self, config: Optional[SignalConfig] = None):
        self.config = config or SignalConfig()
        self.logger = logging.getLogger("signal_generator")
        
        # Signal history for tracking
        self.signal_history: List[TradingSignal] = []
        
        self.logger.info("SignalGenerator initialized")
    
    def generate_signals(self, df: pd.DataFrame) -> List[TradingSignal]:
        """
        Generate trading signals from features DataFrame
        
        Args:
            df: DataFrame with engineered features
            
        Returns:
            List of TradingSignal objects
        """
        if df.empty:
            return []
        
        self.logger.info(f"Generating signals for {len(df['symbol'].unique())} symbols")
        
        all_signals = []
        
        # Process each symbol separately
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol].copy().sort_values('timestamp')
            
            if len(symbol_df) < 10:  # Need minimum data for signals
                continue
            
            # Generate different types of signals
            mean_reversion_signals = self._generate_mean_reversion_signals(symbol_df)
            momentum_signals = self._generate_momentum_signals(symbol_df)
            volume_signals = self._generate_volume_signals(symbol_df)
            
            # Combine signals using multi-factor approach
            combined_signals = self._combine_signals(
                symbol_df, mean_reversion_signals, momentum_signals, volume_signals
            )
            
            all_signals.extend(combined_signals)
        
        # Filter and validate signals
        filtered_signals = self._filter_signals(all_signals, df)
        
        # Store in history
        self.signal_history.extend(filtered_signals)
        
        self.logger.info(f"Generated {len(filtered_signals)} signals from {len(all_signals)} raw signals")
        return filtered_signals
    
    def _generate_mean_reversion_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals"""
        signals_df = df.copy()
        signals_df['mean_reversion_score'] = 0.0
        
        # RSI-based signals
        if 'rsi' in df.columns:
            # Oversold conditions (buy signals)
            oversold_condition = (df['rsi'] < 30) & (df['rsi'].shift(1) >= 30)
            signals_df.loc[oversold_condition, 'mean_reversion_score'] += 0.4
            
            # Overbought conditions (sell signals) 
            overbought_condition = (df['rsi'] > 70) & (df['rsi'].shift(1) <= 70)
            signals_df.loc[overbought_condition, 'mean_reversion_score'] -= 0.4
            
            # RSI divergence
            if 'rsi_momentum' in df.columns:
                price_momentum = df['close'].pct_change()
                rsi_divergence = np.sign(price_momentum) != np.sign(df['rsi_momentum'])
                signals_df.loc[rsi_divergence, 'mean_reversion_score'] += 0.2
        
        # Bollinger Bands signals
        if 'bb_position' in df.columns:
            # Below lower band (buy signal)
            below_bb_lower = df['bb_position'] < 0.1
            signals_df.loc[below_bb_lower, 'mean_reversion_score'] += 0.3
            
            # Above upper band (sell signal)
            above_bb_upper = df['bb_position'] > 0.9
            signals_df.loc[above_bb_upper, 'mean_reversion_score'] -= 0.3
            
            # BB squeeze breakout
            if 'bb_squeeze' in df.columns and 'bb_breakout_up' in df.columns:
                squeeze_breakout_up = (df['bb_squeeze'] == 1) & (df['bb_breakout_up'] == 1)
                squeeze_breakout_down = (df['bb_squeeze'] == 1) & (df['bb_breakout_down'] == 1)
                signals_df.loc[squeeze_breakout_up, 'mean_reversion_score'] += 0.25
                signals_df.loc[squeeze_breakout_down, 'mean_reversion_score'] -= 0.25
        
        # Cross-sectional mean reversion
        if 'return_1d_cs_zscore' in df.columns:
            # Extreme negative returns (buy signal)
            extreme_negative = df['return_1d_cs_zscore'] < -2.0
            signals_df.loc[extreme_negative, 'mean_reversion_score'] += 0.2
            
            # Extreme positive returns (sell signal)
            extreme_positive = df['return_1d_cs_zscore'] > 2.0
            signals_df.loc[extreme_positive, 'mean_reversion_score'] -= 0.2
        
        return signals_df
    
    def _generate_momentum_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals"""
        signals_df = df.copy()
        signals_df['momentum_score'] = 0.0
        
        # MACD signals
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # MACD crossover (bullish)
            macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
            signals_df.loc[macd_bullish, 'momentum_score'] += 0.4
            
            # MACD crossover (bearish)
            macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
            signals_df.loc[macd_bearish, 'momentum_score'] -= 0.4
            
            # MACD histogram momentum
            if 'macd_histogram' in df.columns:
                hist_increasing = df['macd_histogram'] > df['macd_histogram'].shift(1)
                hist_decreasing = df['macd_histogram'] < df['macd_histogram'].shift(1)
                signals_df.loc[hist_increasing, 'momentum_score'] += 0.2
                signals_df.loc[hist_decreasing, 'momentum_score'] -= 0.2
        
        # Moving average trends
        sma_cols = [col for col in df.columns if col.startswith('sma_') and col.endswith('_above')]
        if sma_cols:
            # Count how many MAs price is above
            ma_above_count = df[sma_cols].sum(axis=1)
            ma_score = (ma_above_count / len(sma_cols) - 0.5) * 0.6  # Center around 0
            signals_df['momentum_score'] += ma_score
        
        # Golden/Death cross
        if 'golden_cross' in df.columns:
            signals_df.loc[df['golden_cross'] == 1, 'momentum_score'] += 0.5
        if 'death_cross' in df.columns:
            signals_df.loc[df['death_cross'] == 1, 'momentum_score'] -= 0.5
        
        # Price momentum
        if 'return_1d' in df.columns:
            # Short-term momentum
            strong_up_move = df['return_1d'] > 0.03  # >3% move
            strong_down_move = df['return_1d'] < -0.03  # <-3% move
            signals_df.loc[strong_up_move, 'momentum_score'] += 0.3
            signals_df.loc[strong_down_move, 'momentum_score'] -= 0.3
        
        # Multi-period momentum consistency
        momentum_cols = [col for col in df.columns if col.startswith('return_') and 'd' in col]
        if len(momentum_cols) >= 3:
            # Check for consistent momentum across periods
            momentum_signs = df[momentum_cols].apply(np.sign, axis=1)
            consistent_up = (momentum_signs == 1).all(axis=1)
            consistent_down = (momentum_signs == -1).all(axis=1)
            signals_df.loc[consistent_up, 'momentum_score'] += 0.25
            signals_df.loc[consistent_down, 'momentum_score'] -= 0.25
        
        return signals_df
    
    def _generate_volume_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate volume-based signals"""
        signals_df = df.copy()
        signals_df['volume_score'] = 0.0
        
        if 'volume' not in df.columns:
            return signals_df
        
        # Volume breakout
        if 'volume_breakout' in df.columns:
            # High volume with price increase
            volume_breakout_up = (df['volume_breakout'] == 1) & (df['return_1d'] > 0)
            volume_breakout_down = (df['volume_breakout'] == 1) & (df['return_1d'] < 0)
            signals_df.loc[volume_breakout_up, 'volume_score'] += 0.4
            signals_df.loc[volume_breakout_down, 'volume_score'] -= 0.4
        
        # Volume-price trend
        if 'volume_price_trend' in df.columns:
            positive_vpt = df['volume_price_trend'] > 0
            negative_vpt = df['volume_price_trend'] < 0
            signals_df.loc[positive_vpt, 'volume_score'] += 0.3
            signals_df.loc[negative_vpt, 'volume_score'] -= 0.3
        
        # OBV signals
        if 'obv_momentum' in df.columns:
            obv_increasing = df['obv_momentum'] > 0.02  # >2% OBV increase
            obv_decreasing = df['obv_momentum'] < -0.02  # <-2% OBV decrease
            signals_df.loc[obv_increasing, 'volume_score'] += 0.2
            signals_df.loc[obv_decreasing, 'volume_score'] -= 0.2
        
        # Volume confirmation
        if 'volume_ratio' in df.columns:
            high_volume = df['volume_ratio'] > 1.5  # >150% of average volume
            low_volume = df['volume_ratio'] < 0.5   # <50% of average volume
            
            # High volume confirms signals
            signals_df.loc[high_volume, 'volume_score'] *= 1.2
            # Low volume weakens signals
            signals_df.loc[low_volume, 'volume_score'] *= 0.8
        
        return signals_df
    
    def _combine_signals(self, df: pd.DataFrame, mean_rev: pd.DataFrame, 
                        momentum: pd.DataFrame, volume: pd.DataFrame) -> List[TradingSignal]:
        """Combine different signal types into final signals"""
        signals = []
        
        # Combine scores with weights
        combined_score = (
            mean_rev['mean_reversion_score'] * self.config.mean_reversion_weight +
            momentum['momentum_score'] * self.config.momentum_weight +
            volume['volume_score'] * self.config.volume_weight
        )
        
        # Add ML enhancement if enabled
        if self.config.enable_ml_signals:
            ml_score = self._generate_ml_signals(df)
            combined_score = 0.7 * combined_score + 0.3 * ml_score
        
        # Generate signals from combined scores
        for idx, row in df.iterrows():
            score = combined_score.iloc[idx] if idx < len(combined_score) else 0
            
            # Determine signal type and strength
            if abs(score) < self.config.signal_threshold:
                continue  # No signal
            
            signal_type = SignalType.BUY if score > 0 else SignalType.SELL
            
            # Determine strength
            if abs(score) >= self.config.strong_signal_threshold:
                strength = SignalStrength.STRONG
            elif abs(score) >= self.config.signal_threshold * 1.3:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
            
            # Calculate confidence
            confidence = min(abs(score), 1.0)
            
            # Calculate position size based on confidence and strength
            base_size = self.config.max_position_size
            if strength == SignalStrength.STRONG:
                position_size = base_size * confidence
            elif strength == SignalStrength.MODERATE:
                position_size = base_size * 0.7 * confidence
            else:
                position_size = base_size * 0.4 * confidence
            
            # Calculate target and stop loss
            current_price = row['close']
            if signal_type == SignalType.BUY:
                target_price = current_price * (1 + self.config.take_profit_pct)
                stop_loss = current_price * (1 - self.config.stop_loss_pct)
            else:
                target_price = current_price * (1 - self.config.take_profit_pct)
                stop_loss = current_price * (1 + self.config.stop_loss_pct)
            
            # Create signal
            signal = TradingSignal(
                symbol=row['symbol'],
                timestamp=row['timestamp'],
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                strategy="multi_factor",
                metadata={
                    'mean_reversion_score': mean_rev['mean_reversion_score'].iloc[idx],
                    'momentum_score': momentum['momentum_score'].iloc[idx],
                    'volume_score': volume['volume_score'].iloc[idx],
                    'combined_score': score,
                    'rsi': row.get('rsi', None),
                    'volume_ratio': row.get('volume_ratio', None)
                }
            )
            
            signals.append(signal)
        
        return signals
    
    def _generate_ml_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate ML-based signals (simplified version)"""
        # This is a simplified ML signal - in practice, you'd use trained models
        ml_score = pd.Series(0.0, index=df.index)
        
        # Simple feature-based scoring
        features_to_use = [
            'return_1d_cs_zscore', 'rsi_normalized', 'volume_ratio',
            'bb_position', 'atr_percentile'
        ]
        
        available_features = [f for f in features_to_use if f in df.columns]
        
        if available_features:
            # Weighted combination of normalized features
            feature_weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            
            for i, feature in enumerate(available_features):
                weight = feature_weights[i] if i < len(feature_weights) else 0.1
                feature_values = df[feature].fillna(0)
                
                # Apply simple non-linear transformation
                if feature == 'return_1d_cs_zscore':
                    # Mean reversion signal
                    ml_score += weight * np.tanh(-feature_values)
                elif feature == 'rsi_normalized':
                    # Mean reversion signal
                    ml_score += weight * np.tanh(-feature_values * 2)
                elif feature == 'volume_ratio':
                    # Volume confirmation
                    ml_score += weight * np.tanh((feature_values - 1) * 0.5)
                else:
                    # General momentum signal
                    ml_score += weight * np.tanh(feature_values)
        
        return ml_score
    
    def _filter_signals(self, signals: List[TradingSignal], df: pd.DataFrame) -> List[TradingSignal]:
        """Filter signals based on risk and quality criteria"""
        filtered = []
        
        for signal in signals:
            # Create a mask for the signal's data
            signal_data = df[(df['symbol'] == signal.symbol) & 
                           (df['timestamp'] == signal.timestamp)]
            
            if signal_data.empty:
                continue
            
            row = signal_data.iloc[0]
            
            # Volume filter
            volume_ratio = row.get('volume_ratio', 1.0)
            if volume_ratio < self.config.min_volume_ratio:
                continue
            
            # Volatility filter
            if 'atr_percentile' in row:
                if row['atr_percentile'] > self.config.max_volatility_percentile:
                    continue
            
            # Confidence threshold
            if signal.confidence < self.config.signal_threshold:
                continue
            
            # ML confidence filter (if enabled)
            if self.config.enable_ml_signals and signal.confidence < self.config.ml_confidence_threshold:
                # Only apply strict ML filter for weak signals
                if signal.strength == SignalStrength.WEAK:
                    continue
            
            filtered.append(signal)
        
        return filtered
    
    def get_signal_summary(self, signals: List[TradingSignal]) -> Dict[str, Any]:
        """Get summary statistics of generated signals"""
        if not signals:
            return {"total_signals": 0}
        
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        strong_signals = [s for s in signals if s.strength == SignalStrength.STRONG]
        
        return {
            "total_signals": len(signals),
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "strong_signals": len(strong_signals),
            "avg_confidence": np.mean([s.confidence for s in signals]),
            "avg_position_size": np.mean([s.position_size for s in signals]),
            "symbols_with_signals": len(set(s.symbol for s in signals)),
            "signal_distribution": {
                "strong": len([s for s in signals if s.strength == SignalStrength.STRONG]),
                "moderate": len([s for s in signals if s.strength == SignalStrength.MODERATE]),
                "weak": len([s for s in signals if s.strength == SignalStrength.WEAK])
            }
        }