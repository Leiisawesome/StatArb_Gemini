#!/usr/bin/env python3
"""
Multi-Factor Ensemble Strategy Implementation
Integrates technical momentum indicators with multi-factor framework
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FactorType(Enum):
    """Factor types for multi-factor ensemble"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    QUALITY = "quality"
    RISK = "risk"
    REGIME = "regime"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    TECHNICAL = "technical"  # NEW: Technical indicators factor

@dataclass
class FactorConfig:
    """Configuration for individual factors"""
    factor_type: FactorType
    lookback_period: int
    threshold: float
    weight: float
    indicators: Optional[Dict[str, Any]] = None
    momentum_type: Optional[str] = None
    mean_reversion_threshold: Optional[float] = None
    volatility_metrics: Optional[List[str]] = None

@dataclass
class MultiFactorConfig:
    """Configuration for multi-factor ensemble strategy"""
    factors: List[FactorConfig]
    ensemble_method: str = "adaptive_weighting"
    factor_combination_method: str = "weighted_sum"
    signal_threshold: float = 0.15
    max_factors_per_asset: int = 4
    initial_capital: float = 100000
    max_position_value: float = 10000
    max_positions: int = 15

class MultiFactorEnsembleStrategy:
    """Multi-factor ensemble strategy with technical momentum integration"""
    
    def __init__(self, config: MultiFactorConfig):
        self.config = config
        self.factors = {}
        self.data = None
        self.positions = {}
        self.portfolio_value = config.initial_capital
        self.trade_history = []
        self.factor_signals = {}
        self.performance_metrics = {}
        
        # Initialize factors
        self._initialize_factors()
        
    def _initialize_factors(self):
        """Initialize all factors based on configuration"""
        for factor_config in self.config.factors:
            if factor_config.factor_type == FactorType.TECHNICAL:
                self.factors['technical'] = self._create_technical_factor(factor_config)
            elif factor_config.factor_type == FactorType.MOMENTUM:
                self.factors['momentum'] = self._create_momentum_factor(factor_config)
            elif factor_config.factor_type == FactorType.MEAN_REVERSION:
                self.factors['mean_reversion'] = self._create_mean_reversion_factor(factor_config)
            elif factor_config.factor_type == FactorType.VOLATILITY:
                self.factors['volatility'] = self._create_volatility_factor(factor_config)
                
        logger.info(f"Initialized {len(self.factors)} factors: {list(self.factors.keys())}")
    
    def _create_technical_factor(self, factor_config: FactorConfig) -> Dict:
        """Create technical indicator factor"""
        return {
            'type': 'technical',
            'indicators': factor_config.indicators,
            'lookback_period': factor_config.lookback_period,
            'threshold': factor_config.threshold,
            'weight': factor_config.weight
        }
    
    def _create_momentum_factor(self, factor_config: FactorConfig) -> Dict:
        """Create momentum factor"""
        return {
            'type': 'momentum',
            'lookback_period': factor_config.lookback_period,
            'threshold': factor_config.threshold,
            'weight': factor_config.weight,
            'momentum_type': factor_config.momentum_type
        }
    
    def _create_mean_reversion_factor(self, factor_config: FactorConfig) -> Dict:
        """Create mean reversion factor"""
        return {
            'type': 'mean_reversion',
            'lookback_period': factor_config.lookback_period,
            'threshold': factor_config.threshold,
            'weight': factor_config.weight,
            'mean_reversion_threshold': factor_config.mean_reversion_threshold
        }
    
    def _create_volatility_factor(self, factor_config: FactorConfig) -> Dict:
        """Create volatility factor"""
        return {
            'type': 'volatility',
            'lookback_period': factor_config.lookback_period,
            'threshold': factor_config.threshold,
            'weight': factor_config.weight,
            'volatility_metrics': factor_config.volatility_metrics
        }
    
    def initialize(self, data: Dict[str, pd.DataFrame]):
        """Initialize strategy with data"""
        self.data = data
        logger.info(f"Initialized strategy with {len(data)} symbols")
    
    def generate_signals(self, current_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Generate trading signals for all symbols"""
        signals = {}
        
        logger.info(f"Generating signals for {len(current_data)} symbols")
        
        for symbol, df in current_data.items():
            # Reduce minimum data requirement for testing (from 252 to 60 days)
            if len(df) < 60:  # Need at least 60 days of data for technical indicators
                logger.warning(f"Insufficient data for {symbol}: {len(df)} rows (need 60)")
                continue
                
            logger.info(f"Processing {symbol} with {len(df)} rows of data")
            symbol_signals = {}
            
            # Calculate signals for each factor
            for factor_name, factor_model in self.factors.items():
                try:
                    if factor_name == 'technical':
                        signal = self._calculate_technical_signal(df, factor_model)
                    elif factor_name == 'momentum':
                        signal = self._calculate_momentum_signal(df, factor_model)
                    elif factor_name == 'mean_reversion':
                        signal = self._calculate_mean_reversion_signal(df, factor_model)
                    elif factor_name == 'volatility':
                        signal = self._calculate_volatility_signal(df, factor_model)
                    else:
                        signal = 0.0
                        
                    symbol_signals[factor_name] = signal
                    logger.debug(f"{symbol} {factor_name} signal: {signal:.4f}")
                    
                except Exception as e:
                    logger.error(f"Error calculating {factor_name} signal for {symbol}: {e}")
                    symbol_signals[factor_name] = 0.0
            
            # Combine signals using ensemble method
            combined_signal = self._combine_factor_signals(symbol_signals)
            signals[symbol] = combined_signal
            
            logger.info(f"{symbol} combined signal: {combined_signal:.4f}")
            
            # Store factor signals for analysis
            self.factor_signals[symbol] = symbol_signals
        
        logger.info(f"Generated signals for {len(signals)} symbols")
        return signals
    
    def _calculate_technical_signal(self, df: pd.DataFrame, factor_model: Dict) -> float:
        """Calculate technical indicator signals"""
        try:
            indicators = factor_model['indicators']
            signals = []
            
            # RSI Signal
            rsi = self._calculate_rsi(df, indicators['rsi_period'])
            rsi_signal = self._generate_rsi_signal(rsi, indicators)
            signals.append(rsi_signal)
            
            # MACD Signal
            macd = self._calculate_macd(df, indicators)
            macd_signal = self._generate_macd_signal(macd, indicators)
            signals.append(macd_signal)
            
            # Bollinger Bands Signal
            bb = self._calculate_bollinger_bands(df, indicators)
            bb_signal = self._generate_bb_signal(bb, indicators)
            signals.append(bb_signal)
            
            # Combine signals (equal weight)
            combined_signal = np.mean(signals)
            
            # Apply threshold
            if abs(combined_signal) < factor_model['threshold']:
                combined_signal = 0.0
                
            return combined_signal
            
        except Exception as e:
            logger.error(f"Error calculating technical signal: {e}")
            return 0.0
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _generate_rsi_signal(self, rsi: pd.Series, indicators: Dict) -> float:
        """Generate RSI signal"""
        if len(rsi) == 0:
            return 0.0
            
        current_rsi = rsi.iloc[-1]
        oversold = indicators['rsi_oversold']
        overbought = indicators['rsi_overbought']
        
        if current_rsi < oversold:
            return 0.5  # Buy signal
        elif current_rsi > overbought:
            return -0.5  # Sell signal
        else:
            return 0.0  # Neutral
    
    def _calculate_macd(self, df: pd.DataFrame, indicators: Dict) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        fast_ema = df['close'].ewm(span=indicators['macd_fast']).mean()
        slow_ema = df['close'].ewm(span=indicators['macd_slow']).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=indicators['macd_signal']).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }
    
    def _generate_macd_signal(self, macd: Dict[str, pd.Series], indicators: Dict) -> float:
        """Generate MACD signal"""
        if len(macd['macd_line']) < 2:
            return 0.0
            
        current_macd = macd['macd_line'].iloc[-1]
        current_signal = macd['signal_line'].iloc[-1]
        current_histogram = macd['histogram'].iloc[-1]
        prev_histogram = macd['histogram'].iloc[-2]
        
        threshold = indicators['macd_threshold']
        
        # MACD crossover signal
        if current_macd > current_signal and abs(current_macd - current_signal) > threshold:
            return 0.5  # Buy signal
        elif current_macd < current_signal and abs(current_macd - current_signal) > threshold:
            return -0.5  # Sell signal
        else:
            return 0.0  # Neutral
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, indicators: Dict) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        period = indicators['bollinger_period']
        std_dev = indicators['bollinger_std']
        
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        bandwidth = (upper_band - lower_band) / sma
        
        return {
            'upper': upper_band,
            'lower': lower_band,
            'middle': sma,
            'bandwidth': bandwidth
        }
    
    def _generate_bb_signal(self, bb: Dict[str, pd.Series], indicators: Dict) -> float:
        """Generate Bollinger Bands signal"""
        if len(bb['upper']) == 0:
            return 0.0
            
        current_price = bb['middle'].iloc[-1]  # Use middle band as proxy for current price
        current_upper = bb['upper'].iloc[-1]
        current_lower = bb['lower'].iloc[-1]
        current_bandwidth = bb['bandwidth'].iloc[-1]
        
        threshold = indicators['bollinger_threshold']
        
        # Price relative to bands
        if current_price <= current_lower:
            return 0.5  # Buy signal (oversold)
        elif current_price >= current_upper:
            return -0.5  # Sell signal (overbought)
        else:
            return 0.0  # Neutral
    
    def _calculate_momentum_signal(self, df: pd.DataFrame, factor_model: Dict) -> float:
        """Calculate momentum signal"""
        try:
            lookback = factor_model['lookback_period']
            if len(df) < lookback:
                return 0.0
                
            # Calculate momentum (price change over lookback period)
            current_price = df['close'].iloc[-1]
            past_price = df['close'].iloc[-lookback]
            momentum = (current_price - past_price) / past_price
            
            # Apply threshold
            threshold = factor_model['threshold']
            if abs(momentum) < threshold:
                return 0.0
                
            return np.clip(momentum, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating momentum signal: {e}")
            return 0.0
    
    def _calculate_mean_reversion_signal(self, df: pd.DataFrame, factor_model: Dict) -> float:
        """Calculate mean reversion signal"""
        try:
            lookback = factor_model['lookback_period']
            if len(df) < lookback:
                return 0.0
                
            # Calculate mean reversion signal
            current_price = df['close'].iloc[-1]
            mean_price = df['close'].rolling(window=lookback).mean().iloc[-1]
            
            # Price deviation from mean
            deviation = (current_price - mean_price) / mean_price
            
            # Apply threshold
            threshold = factor_model['threshold']
            if abs(deviation) < threshold:
                return 0.0
                
            # Mean reversion signal (opposite of deviation)
            signal = -deviation
            return np.clip(signal, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating mean reversion signal: {e}")
            return 0.0
    
    def _calculate_volatility_signal(self, df: pd.DataFrame, factor_model: Dict) -> float:
        """Calculate volatility signal"""
        try:
            lookback = factor_model['lookback_period']
            if len(df) < lookback:
                return 0.0
                
            # Calculate rolling volatility
            returns = df['close'].pct_change()
            volatility = returns.rolling(window=lookback).std().iloc[-1]
            
            # Volatility signal (higher volatility = lower signal)
            signal = 1.0 - volatility  # Inverse relationship
            return np.clip(signal, -1.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating volatility signal: {e}")
            return 0.0
    
    def _combine_factor_signals(self, symbol_signals: Dict[str, float]) -> float:
        """Combine factor signals using weighted sum"""
        combined_signal = 0.0
        total_weight = 0.0
        
        for factor_name, signal in symbol_signals.items():
            if factor_name in self.factors:
                weight = self.factors[factor_name]['weight']
                combined_signal += signal * weight
                total_weight += weight
        
        if total_weight > 0:
            combined_signal /= total_weight
        
        # Apply overall signal threshold (reduced for testing)
        # Original: self.config.signal_threshold (0.15)
        # Testing: 0.05 (lower threshold to generate more signals)
        test_threshold = 0.05
        if abs(combined_signal) < test_threshold:
            combined_signal = 0.0
            
        return combined_signal
    
    def calculate_positions(self, signals: Dict[str, float], current_prices: Dict[str, float]) -> Dict[str, Dict]:
        """Calculate target positions based on signals"""
        positions = {}
        
        # Sort signals by absolute value (strongest signals first)
        sorted_signals = sorted(signals.items(), key=lambda x: abs(x[1]), reverse=True)
        
        available_capital = self.portfolio_value * 0.95  # 95% utilization
        used_capital = 0.0
        position_count = 0
        
        for symbol, signal in sorted_signals:
            if position_count >= self.config.max_positions:
                break
                
            if abs(signal) < self.config.signal_threshold:
                continue
                
            current_price = current_prices.get(symbol, 0)
            if current_price <= 0:
                continue
            
            # Calculate position size
            position_value = min(
                self.config.max_position_value,
                available_capital * abs(signal) * 0.1  # Max 10% per signal strength
            )
            
            if used_capital + position_value > available_capital:
                break
                
            # Calculate quantity
            quantity = position_value / current_price
            
            # Determine side
            side = 'LONG' if signal > 0 else 'SHORT'
            
            positions[symbol] = {
                'side': side,
                'quantity': quantity,
                'value': position_value,
                'signal_strength': signal,
                'entry_price': current_price
            }
            
            used_capital += position_value
            position_count += 1
        
        return positions
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        return {
            'portfolio_value': self.portfolio_value,
            'total_positions': len(self.positions),
            'factor_signals': self.factor_signals,
            'trade_history': self.trade_history
        }
    
    def get_strategy_summary(self) -> str:
        """Get strategy summary"""
        return f"MultiFactorEnsembleStrategy with {len(self.factors)} factors: {list(self.factors.keys())}" 