"""
Multi-Strategy Framework
========================

This module implements a comprehensive multi-strategy quantitative trading framework
that integrates multiple trading strategies including statistical arbitrage, momentum,
mean reversion, and volatility strategies with intelligent allocation and rotation.

Key Features:
- Multiple strategy implementations with unified interface
- Dynamic strategy allocation based on market conditions
- Cross-strategy correlation management and optimization
- Performance attribution and strategy rotation
- Risk-adjusted strategy selection and weighting

Author: Pro Quant Desk Trader
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import json
import sqlite3
import threading
import time
from collections import defaultdict, deque

# Statistical and ML libraries
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import sharpe_ratio
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Types of trading strategies"""
    STATISTICAL_ARBITRAGE = "STATISTICAL_ARBITRAGE"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY = "VOLATILITY"
    PAIRS_TRADING = "PAIRS_TRADING"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    CONTRARIAN = "CONTRARIAN"
    MARKET_NEUTRAL = "MARKET_NEUTRAL"

class MarketRegime(Enum):
    """Market regime types for strategy allocation"""
    BULL_TRENDING = "BULL_TRENDING"
    BEAR_TRENDING = "BEAR_TRENDING"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CRISIS = "CRISIS"
    RECOVERY = "RECOVERY"

class AllocationMethod(Enum):
    """Strategy allocation methods"""
    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    RISK_PARITY = "RISK_PARITY"
    PERFORMANCE_BASED = "PERFORMANCE_BASED"
    KELLY_CRITERION = "KELLY_CRITERION"
    BLACK_LITTERMAN = "BLACK_LITTERMAN"
    REGIME_BASED = "REGIME_BASED"

@dataclass
class StrategySignal:
    """Individual strategy signal"""
    strategy_type: StrategyType
    symbol: str
    timestamp: datetime
    
    # Signal details
    signal_strength: float  # -1 to 1
    confidence: float      # 0 to 1
    holding_period: int    # Expected holding period in minutes
    
    # Position details
    target_position: float  # Target position size
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # Risk metrics
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    max_drawdown_estimate: float = 0.0
    
    # Strategy-specific data
    strategy_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    strategy_type: StrategyType
    timestamp: datetime
    
    # Performance metrics
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    
    # Risk metrics
    volatility: float
    var_95: float
    expected_shortfall: float
    
    # Trading metrics
    num_trades: int
    avg_trade_duration: float
    avg_profit_per_trade: float
    
    # Attribution
    alpha: float
    beta: float
    information_ratio: float
    
    # Market context
    market_regime: MarketRegime
    
    # Period data
    period_start: datetime
    period_end: datetime

@dataclass
class StrategyAllocation:
    """Strategy allocation weights"""
    timestamp: datetime
    allocations: Dict[StrategyType, float]
    
    # Allocation metadata
    allocation_method: AllocationMethod
    market_regime: MarketRegime
    
    # Risk metrics
    portfolio_volatility: float
    portfolio_var: float
    diversification_ratio: float
    
    # Constraints
    max_allocation: float = 0.5
    min_allocation: float = 0.0
    
    # Rebalancing
    last_rebalance: datetime = field(default_factory=datetime.now)
    rebalance_frequency: timedelta = timedelta(days=7)

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, strategy_type: StrategyType, config: Dict[str, Any]):
        self.strategy_type = strategy_type
        self.config = config
        self.performance_history: List[StrategyPerformance] = []
        self.signal_history: List[StrategySignal] = []
        
        # Strategy parameters
        self.lookback_period = config.get('lookback_period', 252)
        self.min_observations = config.get('min_observations', 50)
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        
        # Risk parameters
        self.max_position_size = config.get('max_position_size', 0.1)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.05)
        self.take_profit_pct = config.get('take_profit_pct', 0.1)
        
        # Performance tracking
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
    
    @abstractmethod
    def generate_signals(self, market_data: pd.DataFrame) -> List[StrategySignal]:
        """Generate trading signals based on market data"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: StrategySignal, 
                              portfolio_value: float, 
                              current_positions: Dict[str, float]) -> float:
        """Calculate optimal position size for a signal"""
        pass
    
    def update_performance(self, performance: StrategyPerformance):
        """Update strategy performance metrics"""
        self.performance_history.append(performance)
        
        # Keep only recent performance data
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]
    
    def get_current_performance(self) -> Optional[StrategyPerformance]:
        """Get most recent performance metrics"""
        return self.performance_history[-1] if self.performance_history else None
    
    def get_sharpe_ratio(self, lookback_days: int = 30) -> float:
        """Calculate Sharpe ratio over lookback period"""
        if len(self.performance_history) < lookback_days:
            return 0.0
        
        recent_performance = self.performance_history[-lookback_days:]
        returns = [p.total_return for p in recent_performance]
        
        if not returns or np.std(returns) == 0:
            return 0.0
        
        return np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized

class StatisticalArbitrageStrategy(BaseStrategy):
    """Statistical arbitrage strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(StrategyType.STATISTICAL_ARBITRAGE, config)
        
        # StatArb specific parameters
        self.correlation_threshold = config.get('correlation_threshold', 0.7)
        self.cointegration_threshold = config.get('cointegration_threshold', 0.05)
        self.entry_zscore = config.get('entry_zscore', 2.0)
        self.exit_zscore = config.get('exit_zscore', 0.5)
        
        # Pair tracking
        self.pairs_universe = config.get('pairs_universe', [])
        self.active_pairs = {}
    
    def generate_signals(self, market_data: pd.DataFrame) -> List[StrategySignal]:
        """Generate statistical arbitrage signals"""
        signals = []
        
        try:
            for pair_id, pair_data in self.pairs_universe:
                symbol1, symbol2 = pair_data['symbol1'], pair_data['symbol2']
                
                # Check if we have enough data
                if symbol1 not in market_data.columns or symbol2 not in market_data.columns:
                    continue
                
                # Calculate spread
                prices1 = market_data[symbol1].dropna()
                prices2 = market_data[symbol2].dropna()
                
                if len(prices1) < self.min_observations or len(prices2) < self.min_observations:
                    continue
                
                # Calculate hedge ratio (beta)
                returns1 = prices1.pct_change().dropna()
                returns2 = prices2.pct_change().dropna()
                
                # Align data
                aligned_data = pd.concat([returns1, returns2], axis=1).dropna()
                if len(aligned_data) < self.min_observations:
                    continue
                
                # Calculate hedge ratio
                hedge_ratio = np.cov(aligned_data.iloc[:, 0], aligned_data.iloc[:, 1])[0, 1] / np.var(aligned_data.iloc[:, 1])
                
                # Calculate spread
                spread = prices1.iloc[-1] - hedge_ratio * prices2.iloc[-1]
                
                # Calculate spread statistics
                historical_spreads = prices1 - hedge_ratio * prices2
                spread_mean = historical_spreads.mean()
                spread_std = historical_spreads.std()
                
                if spread_std == 0:
                    continue
                
                # Calculate z-score
                zscore = (spread - spread_mean) / spread_std
                
                # Generate signals based on z-score
                if abs(zscore) > self.entry_zscore:
                    # Entry signal
                    signal_strength = np.sign(-zscore) * min(1.0, abs(zscore) / self.entry_zscore)
                    confidence = min(1.0, abs(zscore) / self.entry_zscore)
                    
                    # Create signals for both legs
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol1,
                        timestamp=datetime.now(),
                        signal_strength=signal_strength,
                        confidence=confidence,
                        holding_period=60,  # 1 hour expected
                        target_position=signal_strength * self.max_position_size,
                        expected_return=abs(zscore) * 0.01,  # Simplified
                        expected_volatility=spread_std,
                        strategy_data={
                            'pair_id': pair_id,
                            'hedge_ratio': hedge_ratio,
                            'zscore': zscore,
                            'leg': 'primary'
                        }
                    ))
                    
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol2,
                        timestamp=datetime.now(),
                        signal_strength=-signal_strength * hedge_ratio,
                        confidence=confidence,
                        holding_period=60,
                        target_position=-signal_strength * hedge_ratio * self.max_position_size,
                        expected_return=abs(zscore) * 0.01,
                        expected_volatility=spread_std,
                        strategy_data={
                            'pair_id': pair_id,
                            'hedge_ratio': hedge_ratio,
                            'zscore': zscore,
                            'leg': 'hedge'
                        }
                    ))
                
                elif pair_id in self.active_pairs and abs(zscore) < self.exit_zscore:
                    # Exit signal
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol1,
                        timestamp=datetime.now(),
                        signal_strength=0.0,  # Exit signal
                        confidence=0.8,
                        holding_period=0,
                        target_position=0.0,
                        strategy_data={
                            'pair_id': pair_id,
                            'zscore': zscore,
                            'action': 'exit'
                        }
                    ))
                    
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol2,
                        timestamp=datetime.now(),
                        signal_strength=0.0,
                        confidence=0.8,
                        holding_period=0,
                        target_position=0.0,
                        strategy_data={
                            'pair_id': pair_id,
                            'zscore': zscore,
                            'action': 'exit'
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error generating StatArb signals: {e}")
        
        return signals
    
    def calculate_position_size(self, signal: StrategySignal, 
                              portfolio_value: float, 
                              current_positions: Dict[str, float]) -> float:
        """Calculate position size for statistical arbitrage"""
        # Risk-adjusted position sizing
        base_size = signal.target_position * portfolio_value
        
        # Adjust for volatility
        if signal.expected_volatility > 0:
            vol_adjustment = 0.2 / signal.expected_volatility  # Target 20% volatility
            base_size *= min(1.0, vol_adjustment)
        
        # Adjust for confidence
        base_size *= signal.confidence
        
        # Apply position limits
        max_position_value = portfolio_value * self.max_position_size
        base_size = np.sign(base_size) * min(abs(base_size), max_position_value)
        
        return base_size

class MomentumStrategy(BaseStrategy):
    """Momentum strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(StrategyType.MOMENTUM, config)
        
        # Momentum specific parameters
        self.momentum_lookback = config.get('momentum_lookback', 20)
        self.momentum_threshold = config.get('momentum_threshold', 0.02)
        self.trend_strength_threshold = config.get('trend_strength_threshold', 0.6)
        
        # Technical indicators
        self.use_rsi = config.get('use_rsi', True)
        self.use_macd = config.get('use_macd', True)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
    
    def generate_signals(self, market_data: pd.DataFrame) -> List[StrategySignal]:
        """Generate momentum signals"""
        signals = []
        
        try:
            for symbol in market_data.columns:
                prices = market_data[symbol].dropna()
                
                if len(prices) < self.momentum_lookback + 20:
                    continue
                
                # Calculate momentum
                momentum = (prices.iloc[-1] / prices.iloc[-self.momentum_lookback] - 1)
                
                # Calculate trend strength
                returns = prices.pct_change().dropna()
                trend_strength = self._calculate_trend_strength(returns)
                
                # Calculate RSI if enabled
                rsi = self._calculate_rsi(prices) if self.use_rsi else 50
                
                # Calculate MACD if enabled
                macd_signal = self._calculate_macd_signal(prices) if self.use_macd else 0
                
                # Generate signal
                signal_strength = 0.0
                confidence = 0.0
                
                if momentum > self.momentum_threshold and trend_strength > self.trend_strength_threshold:
                    # Bullish momentum
                    signal_strength = min(1.0, momentum / (self.momentum_threshold * 2))
                    confidence = trend_strength
                    
                    # Adjust for RSI
                    if self.use_rsi and rsi > self.rsi_overbought:
                        signal_strength *= 0.5  # Reduce signal in overbought territory
                    
                    # Adjust for MACD
                    if self.use_macd:
                        signal_strength *= (1 + macd_signal * 0.2)
                
                elif momentum < -self.momentum_threshold and trend_strength > self.trend_strength_threshold:
                    # Bearish momentum
                    signal_strength = max(-1.0, momentum / (self.momentum_threshold * 2))
                    confidence = trend_strength
                    
                    # Adjust for RSI
                    if self.use_rsi and rsi < self.rsi_oversold:
                        signal_strength *= 0.5  # Reduce signal in oversold territory
                    
                    # Adjust for MACD
                    if self.use_macd:
                        signal_strength *= (1 + macd_signal * 0.2)
                
                if abs(signal_strength) > 0.1 and confidence > 0.5:
                    # Calculate expected metrics
                    volatility = returns.tail(20).std() * np.sqrt(252)
                    expected_return = signal_strength * momentum
                    
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol,
                        timestamp=datetime.now(),
                        signal_strength=signal_strength,
                        confidence=confidence,
                        holding_period=self.momentum_lookback * 30,  # Hold for momentum period
                        target_position=signal_strength * self.max_position_size,
                        expected_return=expected_return,
                        expected_volatility=volatility,
                        strategy_data={
                            'momentum': momentum,
                            'trend_strength': trend_strength,
                            'rsi': rsi,
                            'macd_signal': macd_signal
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error generating momentum signals: {e}")
        
        return signals
    
    def _calculate_trend_strength(self, returns: pd.Series) -> float:
        """Calculate trend strength using various metrics"""
        if len(returns) < 20:
            return 0.0
        
        # Calculate directional consistency
        positive_days = (returns > 0).sum()
        total_days = len(returns)
        directional_consistency = abs(positive_days / total_days - 0.5) * 2
        
        # Calculate trend persistence
        cumulative_returns = (1 + returns).cumprod()
        trend_persistence = abs(stats.pearsonr(range(len(cumulative_returns)), cumulative_returns)[0])
        
        return (directional_consistency + trend_persistence) / 2
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd_signal(self, prices: pd.Series) -> float:
        """Calculate MACD signal"""
        if len(prices) < 26:
            return 0.0
        
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9).mean()
        
        macd_histogram = macd - signal_line
        
        # Return normalized signal
        return np.sign(macd_histogram.iloc[-1]) * min(1.0, abs(macd_histogram.iloc[-1]) / prices.iloc[-1] * 1000)
    
    def calculate_position_size(self, signal: StrategySignal, 
                              portfolio_value: float, 
                              current_positions: Dict[str, float]) -> float:
        """Calculate position size for momentum strategy"""
        # Base position size
        base_size = signal.target_position * portfolio_value
        
        # Adjust for momentum strength
        momentum = signal.strategy_data.get('momentum', 0.0)
        momentum_adjustment = min(1.5, 1.0 + abs(momentum))
        base_size *= momentum_adjustment
        
        # Adjust for trend strength
        trend_strength = signal.strategy_data.get('trend_strength', 0.0)
        base_size *= trend_strength
        
        # Volatility adjustment
        if signal.expected_volatility > 0:
            vol_target = 0.25  # Target 25% volatility for momentum
            vol_adjustment = vol_target / signal.expected_volatility
            base_size *= min(1.5, vol_adjustment)
        
        # Apply position limits
        max_position_value = portfolio_value * self.max_position_size
        base_size = np.sign(base_size) * min(abs(base_size), max_position_value)
        
        return base_size

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(StrategyType.MEAN_REVERSION, config)
        
        # Mean reversion parameters
        self.reversion_lookback = config.get('reversion_lookback', 20)
        self.deviation_threshold = config.get('deviation_threshold', 2.0)
        self.mean_reversion_strength_threshold = config.get('mean_reversion_strength_threshold', 0.6)
        
        # Bollinger Bands parameters
        self.bb_period = config.get('bb_period', 20)
        self.bb_std = config.get('bb_std', 2.0)
    
    def generate_signals(self, market_data: pd.DataFrame) -> List[StrategySignal]:
        """Generate mean reversion signals"""
        signals = []
        
        try:
            for symbol in market_data.columns:
                prices = market_data[symbol].dropna()
                
                if len(prices) < self.reversion_lookback + 20:
                    continue
                
                # Calculate rolling statistics
                rolling_mean = prices.rolling(window=self.reversion_lookback).mean()
                rolling_std = prices.rolling(window=self.reversion_lookback).std()
                
                # Calculate z-score
                current_price = prices.iloc[-1]
                mean_price = rolling_mean.iloc[-1]
                std_price = rolling_std.iloc[-1]
                
                if std_price == 0:
                    continue
                
                zscore = (current_price - mean_price) / std_price
                
                # Calculate mean reversion strength
                returns = prices.pct_change().dropna()
                reversion_strength = self._calculate_mean_reversion_strength(returns)
                
                # Calculate Bollinger Bands
                bb_upper, bb_lower = self._calculate_bollinger_bands(prices)
                
                # Generate signals
                signal_strength = 0.0
                confidence = 0.0
                
                if zscore > self.deviation_threshold and reversion_strength > self.mean_reversion_strength_threshold:
                    # Price is too high, expect reversion down
                    signal_strength = -min(1.0, zscore / self.deviation_threshold)
                    confidence = reversion_strength
                    
                    # Adjust for Bollinger Bands
                    if current_price > bb_upper:
                        signal_strength *= 1.2  # Stronger signal
                
                elif zscore < -self.deviation_threshold and reversion_strength > self.mean_reversion_strength_threshold:
                    # Price is too low, expect reversion up
                    signal_strength = min(1.0, abs(zscore) / self.deviation_threshold)
                    confidence = reversion_strength
                    
                    # Adjust for Bollinger Bands
                    if current_price < bb_lower:
                        signal_strength *= 1.2  # Stronger signal
                
                if abs(signal_strength) > 0.1 and confidence > 0.5:
                    # Calculate expected metrics
                    volatility = returns.tail(20).std() * np.sqrt(252)
                    expected_return = signal_strength * abs(zscore) * 0.01
                    
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol,
                        timestamp=datetime.now(),
                        signal_strength=signal_strength,
                        confidence=confidence,
                        holding_period=self.reversion_lookback * 20,  # Shorter holding period
                        target_position=signal_strength * self.max_position_size,
                        expected_return=expected_return,
                        expected_volatility=volatility,
                        strategy_data={
                            'zscore': zscore,
                            'reversion_strength': reversion_strength,
                            'bb_position': (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error generating mean reversion signals: {e}")
        
        return signals
    
    def _calculate_mean_reversion_strength(self, returns: pd.Series) -> float:
        """Calculate mean reversion strength"""
        if len(returns) < 20:
            return 0.0
        
        # Calculate autocorrelation at lag 1
        autocorr = returns.autocorr(lag=1)
        
        # Mean reversion is indicated by negative autocorrelation
        reversion_strength = max(0.0, -autocorr) if not np.isnan(autocorr) else 0.0
        
        # Calculate Hurst exponent for additional confirmation
        hurst = self._calculate_hurst_exponent(returns)
        
        # Hurst < 0.5 indicates mean reversion
        hurst_contribution = max(0.0, (0.5 - hurst) * 2) if not np.isnan(hurst) else 0.0
        
        return (reversion_strength + hurst_contribution) / 2
    
    def _calculate_hurst_exponent(self, returns: pd.Series) -> float:
        """Calculate Hurst exponent"""
        try:
            if len(returns) < 20:
                return 0.5
            
            # Convert returns to price series
            prices = (1 + returns).cumprod()
            
            # Calculate R/S statistic
            lags = range(2, min(len(prices) // 2, 20))
            rs_values = []
            
            for lag in lags:
                # Split series into segments
                segments = [prices[i:i+lag] for i in range(0, len(prices)-lag+1, lag)]
                
                rs_segment_values = []
                for segment in segments:
                    if len(segment) == lag:
                        mean_segment = np.mean(segment)
                        deviations = segment - mean_segment
                        cumulative_deviations = np.cumsum(deviations)
                        
                        R = np.max(cumulative_deviations) - np.min(cumulative_deviations)
                        S = np.std(segment)
                        
                        if S > 0:
                            rs_segment_values.append(R / S)
                
                if rs_segment_values:
                    rs_values.append(np.mean(rs_segment_values))
            
            if len(rs_values) < 2:
                return 0.5
            
            # Linear regression to find Hurst exponent
            log_lags = np.log(lags[:len(rs_values)])
            log_rs = np.log(rs_values)
            
            slope, _, _, _, _ = stats.linregress(log_lags, log_rs)
            
            return slope
            
        except Exception:
            return 0.5
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < self.bb_period:
            current_price = prices.iloc[-1]
            return current_price * 1.02, current_price * 0.98
        
        rolling_mean = prices.rolling(window=self.bb_period).mean().iloc[-1]
        rolling_std = prices.rolling(window=self.bb_period).std().iloc[-1]
        
        upper_band = rolling_mean + (rolling_std * self.bb_std)
        lower_band = rolling_mean - (rolling_std * self.bb_std)
        
        return upper_band, lower_band
    
    def calculate_position_size(self, signal: StrategySignal, 
                              portfolio_value: float, 
                              current_positions: Dict[str, float]) -> float:
        """Calculate position size for mean reversion strategy"""
        # Base position size
        base_size = signal.target_position * portfolio_value
        
        # Adjust for reversion strength
        reversion_strength = signal.strategy_data.get('reversion_strength', 0.0)
        base_size *= reversion_strength
        
        # Adjust for z-score magnitude
        zscore = signal.strategy_data.get('zscore', 0.0)
        zscore_adjustment = min(1.5, 1.0 + abs(zscore) * 0.1)
        base_size *= zscore_adjustment
        
        # Volatility adjustment (mean reversion works better in lower vol)
        if signal.expected_volatility > 0:
            vol_target = 0.15  # Target 15% volatility for mean reversion
            vol_adjustment = vol_target / signal.expected_volatility
            base_size *= min(2.0, vol_adjustment)
        
        # Apply position limits
        max_position_value = portfolio_value * self.max_position_size
        base_size = np.sign(base_size) * min(abs(base_size), max_position_value)
        
        return base_size

class VolatilityStrategy(BaseStrategy):
    """Volatility strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(StrategyType.VOLATILITY, config)
        
        # Volatility parameters
        self.vol_lookback = config.get('vol_lookback', 20)
        self.vol_threshold = config.get('vol_threshold', 0.02)
        self.vol_regime_threshold = config.get('vol_regime_threshold', 0.8)
        
        # VIX parameters
        self.use_vix = config.get('use_vix', True)
        self.vix_low = config.get('vix_low', 15)
        self.vix_high = config.get('vix_high', 30)
    
    def generate_signals(self, market_data: pd.DataFrame) -> List[StrategySignal]:
        """Generate volatility-based signals"""
        signals = []
        
        try:
            for symbol in market_data.columns:
                prices = market_data[symbol].dropna()
                
                if len(prices) < self.vol_lookback + 20:
                    continue
                
                # Calculate returns and volatility
                returns = prices.pct_change().dropna()
                current_vol = returns.tail(self.vol_lookback).std() * np.sqrt(252)
                historical_vol = returns.rolling(window=self.vol_lookback).std() * np.sqrt(252)
                
                # Calculate volatility percentile
                vol_percentile = stats.percentileofscore(historical_vol.dropna(), current_vol) / 100.0
                
                # Calculate volatility regime
                vol_regime = self._calculate_volatility_regime(returns)
                
                # Generate signals based on volatility
                signal_strength = 0.0
                confidence = 0.0
                
                if vol_percentile > 0.8:  # High volatility
                    # In high vol regime, often good for mean reversion or volatility selling
                    signal_strength = -0.5  # Short volatility
                    confidence = vol_percentile
                    
                elif vol_percentile < 0.2:  # Low volatility
                    # In low vol regime, often precedes volatility expansion
                    signal_strength = 0.5  # Long volatility
                    confidence = 1.0 - vol_percentile
                
                # Adjust for VIX if available
                if self.use_vix and 'VIX' in market_data.columns:
                    vix_level = market_data['VIX'].iloc[-1]
                    if vix_level > self.vix_high:
                        signal_strength *= 1.2  # Stronger short vol signal
                    elif vix_level < self.vix_low:
                        signal_strength *= 1.2  # Stronger long vol signal
                
                if abs(signal_strength) > 0.1 and confidence > 0.6:
                    # Calculate expected metrics
                    expected_return = signal_strength * (vol_percentile - 0.5) * 0.02
                    
                    signals.append(StrategySignal(
                        strategy_type=self.strategy_type,
                        symbol=symbol,
                        timestamp=datetime.now(),
                        signal_strength=signal_strength,
                        confidence=confidence,
                        holding_period=self.vol_lookback * 15,  # Medium-term holding
                        target_position=signal_strength * self.max_position_size,
                        expected_return=expected_return,
                        expected_volatility=current_vol,
                        strategy_data={
                            'vol_percentile': vol_percentile,
                            'current_vol': current_vol,
                            'vol_regime': vol_regime,
                            'vix_level': market_data.get('VIX', {}).get(market_data.index[-1], 20) if 'VIX' in market_data.columns else 20
                        }
                    ))
        
        except Exception as e:
            logger.error(f"Error generating volatility signals: {e}")
        
        return signals
    
    def _calculate_volatility_regime(self, returns: pd.Series) -> str:
        """Calculate current volatility regime"""
        if len(returns) < 60:
            return "NORMAL"
        
        # Calculate rolling volatility
        vol_series = returns.rolling(window=20).std() * np.sqrt(252)
        current_vol = vol_series.iloc[-1]
        
        # Calculate percentiles
        vol_25 = vol_series.quantile(0.25)
        vol_75 = vol_series.quantile(0.75)
        vol_90 = vol_series.quantile(0.90)
        vol_10 = vol_series.quantile(0.10)
        
        if current_vol > vol_90:
            return "EXTREME_HIGH"
        elif current_vol > vol_75:
            return "HIGH"
        elif current_vol < vol_10:
            return "EXTREME_LOW"
        elif current_vol < vol_25:
            return "LOW"
        else:
            return "NORMAL"
    
    def calculate_position_size(self, signal: StrategySignal, 
                              portfolio_value: float, 
                              current_positions: Dict[str, float]) -> float:
        """Calculate position size for volatility strategy"""
        # Base position size
        base_size = signal.target_position * portfolio_value
        
        # Adjust for volatility percentile
        vol_percentile = signal.strategy_data.get('vol_percentile', 0.5)
        percentile_adjustment = 1.0 + abs(vol_percentile - 0.5)
        base_size *= percentile_adjustment
        
        # Volatility strategies typically use smaller positions due to higher risk
        base_size *= 0.5
        
        # Apply position limits
        max_position_value = portfolio_value * self.max_position_size * 0.5  # Reduced limit for vol strategies
        base_size = np.sign(base_size) * min(abs(base_size), max_position_value)
        
        return base_size

class MultiStrategyFramework:
    """
    Comprehensive multi-strategy framework that manages multiple trading strategies
    with intelligent allocation and rotation capabilities
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the multi-strategy framework
        
        Args:
            config: Configuration for all strategies and allocation
        """
        self.config = config
        
        # Initialize strategies
        self.strategies: Dict[StrategyType, BaseStrategy] = {}
        self._initialize_strategies()
        
        # Strategy allocation
        self.current_allocation = StrategyAllocation(
            timestamp=datetime.now(),
            allocations={strategy_type: 0.25 for strategy_type in self.strategies.keys()},  # Equal weight initially
            allocation_method=AllocationMethod.EQUAL_WEIGHT,
            market_regime=MarketRegime.SIDEWAYS,
            portfolio_volatility=0.15,
            portfolio_var=0.05
        )
        
        # Performance tracking
        self.strategy_performances: Dict[StrategyType, List[StrategyPerformance]] = defaultdict(list)
        self.allocation_history: List[StrategyAllocation] = []
        
        # Market regime detection
        self.current_market_regime = MarketRegime.SIDEWAYS
        self.regime_history: List[Tuple[datetime, MarketRegime]] = []
        
        # Database for persistence
        self.db_path = config.get('db_path', 'multi_strategy.db')
        self._init_database()
        
        logger.info("Multi-strategy framework initialized")
    
    def _initialize_strategies(self):
        """Initialize all trading strategies"""
        strategy_configs = self.config.get('strategies', {})
        
        # Statistical Arbitrage
        if 'statistical_arbitrage' in strategy_configs:
            self.strategies[StrategyType.STATISTICAL_ARBITRAGE] = StatisticalArbitrageStrategy(
                strategy_configs['statistical_arbitrage']
            )
        
        # Momentum
        if 'momentum' in strategy_configs:
            self.strategies[StrategyType.MOMENTUM] = MomentumStrategy(
                strategy_configs['momentum']
            )
        
        # Mean Reversion
        if 'mean_reversion' in strategy_configs:
            self.strategies[StrategyType.MEAN_REVERSION] = MeanReversionStrategy(
                strategy_configs['mean_reversion']
            )
        
        # Volatility
        if 'volatility' in strategy_configs:
            self.strategies[StrategyType.VOLATILITY] = VolatilityStrategy(
                strategy_configs['volatility']
            )
        
        logger.info(f"Initialized {len(self.strategies)} strategies")
    
    def _init_database(self):
        """Initialize SQLite database for strategy data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    signal_strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    target_position REAL NOT NULL,
                    expected_return REAL,
                    expected_volatility REAL,
                    strategy_data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    total_return REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    market_regime TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_allocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    allocations TEXT NOT NULL,
                    allocation_method TEXT NOT NULL,
                    market_regime TEXT NOT NULL,
                    portfolio_volatility REAL NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Multi-strategy database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def generate_all_signals(self, market_data: pd.DataFrame) -> Dict[StrategyType, List[StrategySignal]]:
        """Generate signals from all strategies"""
        all_signals = {}
        
        for strategy_type, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(market_data)
                all_signals[strategy_type] = signals
                
                # Store signals in database
                self._store_signals(signals)
                
            except Exception as e:
                logger.error(f"Error generating signals for {strategy_type.value}: {e}")
                all_signals[strategy_type] = []
        
        return all_signals
    
    def _store_signals(self, signals: List[StrategySignal]):
        """Store signals in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for signal in signals:
                cursor.execute('''
                    INSERT INTO strategy_signals 
                    (strategy_type, symbol, timestamp, signal_strength, confidence,
                     target_position, expected_return, expected_volatility, strategy_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    signal.strategy_type.value, signal.symbol, signal.timestamp,
                    signal.signal_strength, signal.confidence, signal.target_position,
                    signal.expected_return, signal.expected_volatility,
                    json.dumps(signal.strategy_data)
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing signals: {e}")
    
    def calculate_optimal_allocation(self, method: AllocationMethod = AllocationMethod.RISK_PARITY) -> StrategyAllocation:
        """Calculate optimal strategy allocation"""
        try:
            if method == AllocationMethod.EQUAL_WEIGHT:
                allocations = {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
            
            elif method == AllocationMethod.RISK_PARITY:
                allocations = self._calculate_risk_parity_allocation()
            
            elif method == AllocationMethod.PERFORMANCE_BASED:
                allocations = self._calculate_performance_based_allocation()
            
            elif method == AllocationMethod.REGIME_BASED:
                allocations = self._calculate_regime_based_allocation()
            
            else:
                # Default to equal weight
                allocations = {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
            
            # Calculate portfolio metrics
            portfolio_vol = self._calculate_portfolio_volatility(allocations)
            portfolio_var = self._calculate_portfolio_var(allocations)
            diversification_ratio = self._calculate_diversification_ratio(allocations)
            
            new_allocation = StrategyAllocation(
                timestamp=datetime.now(),
                allocations=allocations,
                allocation_method=method,
                market_regime=self.current_market_regime,
                portfolio_volatility=portfolio_vol,
                portfolio_var=portfolio_var,
                diversification_ratio=diversification_ratio
            )
            
            return new_allocation
            
        except Exception as e:
            logger.error(f"Error calculating optimal allocation: {e}")
            return self.current_allocation
    
    def _calculate_risk_parity_allocation(self) -> Dict[StrategyType, float]:
        """Calculate risk parity allocation"""
        try:
            # Get recent performance data for each strategy
            strategy_vols = {}
            
            for strategy_type, strategy in self.strategies.items():
                recent_performance = strategy.performance_history[-30:] if len(strategy.performance_history) >= 30 else strategy.performance_history
                
                if recent_performance:
                    returns = [p.total_return for p in recent_performance]
                    vol = np.std(returns) if len(returns) > 1 else 0.15  # Default vol
                else:
                    vol = 0.15  # Default volatility
                
                strategy_vols[strategy_type] = max(0.01, vol)  # Minimum vol to avoid division by zero
            
            # Calculate inverse volatility weights
            inv_vols = {strategy_type: 1.0 / vol for strategy_type, vol in strategy_vols.items()}
            total_inv_vol = sum(inv_vols.values())
            
            # Normalize to sum to 1
            allocations = {strategy_type: inv_vol / total_inv_vol for strategy_type, inv_vol in inv_vols.items()}
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating risk parity allocation: {e}")
            return {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
    
    def _calculate_performance_based_allocation(self) -> Dict[StrategyType, float]:
        """Calculate performance-based allocation"""
        try:
            # Get recent Sharpe ratios for each strategy
            strategy_sharpes = {}
            
            for strategy_type, strategy in self.strategies.items():
                sharpe = strategy.get_sharpe_ratio(lookback_days=30)
                strategy_sharpes[strategy_type] = max(0.0, sharpe)  # Only positive Sharpe ratios
            
            total_sharpe = sum(strategy_sharpes.values())
            
            if total_sharpe > 0:
                # Allocate based on Sharpe ratios
                allocations = {strategy_type: sharpe / total_sharpe for strategy_type, sharpe in strategy_sharpes.items()}
            else:
                # Equal weight if no positive Sharpe ratios
                allocations = {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating performance-based allocation: {e}")
            return {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
    
    def _calculate_regime_based_allocation(self) -> Dict[StrategyType, float]:
        """Calculate regime-based allocation"""
        try:
            # Define regime-specific allocations
            regime_allocations = {
                MarketRegime.BULL_TRENDING: {
                    StrategyType.MOMENTUM: 0.4,
                    StrategyType.STATISTICAL_ARBITRAGE: 0.3,
                    StrategyType.MEAN_REVERSION: 0.2,
                    StrategyType.VOLATILITY: 0.1
                },
                MarketRegime.BEAR_TRENDING: {
                    StrategyType.MOMENTUM: 0.3,
                    StrategyType.STATISTICAL_ARBITRAGE: 0.4,
                    StrategyType.MEAN_REVERSION: 0.2,
                    StrategyType.VOLATILITY: 0.1
                },
                MarketRegime.SIDEWAYS: {
                    StrategyType.STATISTICAL_ARBITRAGE: 0.4,
                    StrategyType.MEAN_REVERSION: 0.4,
                    StrategyType.MOMENTUM: 0.1,
                    StrategyType.VOLATILITY: 0.1
                },
                MarketRegime.HIGH_VOLATILITY: {
                    StrategyType.VOLATILITY: 0.4,
                    StrategyType.STATISTICAL_ARBITRAGE: 0.3,
                    StrategyType.MEAN_REVERSION: 0.2,
                    StrategyType.MOMENTUM: 0.1
                },
                MarketRegime.LOW_VOLATILITY: {
                    StrategyType.MOMENTUM: 0.4,
                    StrategyType.STATISTICAL_ARBITRAGE: 0.3,
                    StrategyType.MEAN_REVERSION: 0.2,
                    StrategyType.VOLATILITY: 0.1
                }
            }
            
            # Get allocation for current regime
            target_allocation = regime_allocations.get(self.current_market_regime, {})
            
            # Only include strategies that are actually available
            allocations = {}
            total_weight = 0.0
            
            for strategy_type in self.strategies.keys():
                weight = target_allocation.get(strategy_type, 0.0)
                allocations[strategy_type] = weight
                total_weight += weight
            
            # Normalize if needed
            if total_weight > 0:
                allocations = {strategy_type: weight / total_weight for strategy_type, weight in allocations.items()}
            else:
                # Equal weight fallback
                allocations = {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error calculating regime-based allocation: {e}")
            return {strategy_type: 1.0 / len(self.strategies) for strategy_type in self.strategies.keys()}
    
    def _calculate_portfolio_volatility(self, allocations: Dict[StrategyType, float]) -> float:
        """Calculate portfolio volatility"""
        try:
            # Get strategy volatilities
            strategy_vols = []
            weights = []
            
            for strategy_type, weight in allocations.items():
                if strategy_type in self.strategies:
                    strategy = self.strategies[strategy_type]
                    recent_performance = strategy.performance_history[-30:] if len(strategy.performance_history) >= 30 else strategy.performance_history
                    
                    if recent_performance:
                        returns = [p.total_return for p in recent_performance]
                        vol = np.std(returns) if len(returns) > 1 else 0.15
                    else:
                        vol = 0.15
                    
                    strategy_vols.append(vol)
                    weights.append(weight)
            
            if not strategy_vols:
                return 0.15
            
            # Simple portfolio volatility (assuming zero correlation for now)
            portfolio_vol = np.sqrt(sum(w**2 * v**2 for w, v in zip(weights, strategy_vols)))
            
            return portfolio_vol
            
        except Exception as e:
            logger.error(f"Error calculating portfolio volatility: {e}")
            return 0.15
    
    def _calculate_portfolio_var(self, allocations: Dict[StrategyType, float]) -> float:
        """Calculate portfolio Value-at-Risk"""
        # Simplified VaR calculation
        portfolio_vol = self._calculate_portfolio_volatility(allocations)
        var_95 = 1.645 * portfolio_vol  # 95% VaR assuming normal distribution
        return var_95
    
    def _calculate_diversification_ratio(self, allocations: Dict[StrategyType, float]) -> float:
        """Calculate diversification ratio"""
        try:
            # Diversification ratio = weighted average volatility / portfolio volatility
            strategy_vols = []
            weights = []
            
            for strategy_type, weight in allocations.items():
                if strategy_type in self.strategies:
                    strategy = self.strategies[strategy_type]
                    recent_performance = strategy.performance_history[-30:] if len(strategy.performance_history) >= 30 else strategy.performance_history
                    
                    if recent_performance:
                        returns = [p.total_return for p in recent_performance]
                        vol = np.std(returns) if len(returns) > 1 else 0.15
                    else:
                        vol = 0.15
                    
                    strategy_vols.append(vol)
                    weights.append(weight)
            
            if not strategy_vols:
                return 1.0
            
            weighted_avg_vol = sum(w * v for w, v in zip(weights, strategy_vols))
            portfolio_vol = self._calculate_portfolio_volatility(allocations)
            
            if portfolio_vol > 0:
                diversification_ratio = weighted_avg_vol / portfolio_vol
            else:
                diversification_ratio = 1.0
            
            return diversification_ratio
            
        except Exception as e:
            logger.error(f"Error calculating diversification ratio: {e}")
            return 1.0
    
    def update_market_regime(self, market_data: pd.DataFrame):
        """Update current market regime based on market data"""
        try:
            # Simple regime detection based on market characteristics
            if 'SPY' in market_data.columns:
                spy_prices = market_data['SPY'].dropna()
                
                if len(spy_prices) >= 60:
                    # Calculate returns and volatility
                    returns = spy_prices.pct_change().dropna()
                    recent_returns = returns.tail(20)
                    recent_vol = recent_returns.std() * np.sqrt(252)
                    
                    # Calculate trend
                    trend = (spy_prices.iloc[-1] / spy_prices.iloc[-60] - 1) * 100  # 60-day trend
                    
                    # Determine regime
                    if recent_vol > 0.25:  # High volatility
                        if trend > 5:
                            new_regime = MarketRegime.BULL_TRENDING
                        elif trend < -5:
                            new_regime = MarketRegime.BEAR_TRENDING
                        else:
                            new_regime = MarketRegime.HIGH_VOLATILITY
                    elif recent_vol < 0.12:  # Low volatility
                        new_regime = MarketRegime.LOW_VOLATILITY
                    else:  # Normal volatility
                        if trend > 3:
                            new_regime = MarketRegime.BULL_TRENDING
                        elif trend < -3:
                            new_regime = MarketRegime.BEAR_TRENDING
                        else:
                            new_regime = MarketRegime.SIDEWAYS
                    
                    # Update regime if changed
                    if new_regime != self.current_market_regime:
                        self.current_market_regime = new_regime
                        self.regime_history.append((datetime.now(), new_regime))
                        logger.info(f"Market regime changed to {new_regime.value}")
                        
                        # Trigger allocation update
                        self.update_allocation(AllocationMethod.REGIME_BASED)
            
        except Exception as e:
            logger.error(f"Error updating market regime: {e}")
    
    def update_allocation(self, method: AllocationMethod = None):
        """Update strategy allocation"""
        try:
            if method is None:
                method = self.current_allocation.allocation_method
            
            new_allocation = self.calculate_optimal_allocation(method)
            
            # Check if significant change is needed
            allocation_change = sum(abs(new_allocation.allocations.get(st, 0) - self.current_allocation.allocations.get(st, 0)) 
                                  for st in self.strategies.keys())
            
            if allocation_change > 0.1:  # 10% threshold for rebalancing
                self.current_allocation = new_allocation
                self.allocation_history.append(new_allocation)
                
                # Store in database
                self._store_allocation(new_allocation)
                
                logger.info(f"Strategy allocation updated: {new_allocation.allocations}")
            
        except Exception as e:
            logger.error(f"Error updating allocation: {e}")
    
    def _store_allocation(self, allocation: StrategyAllocation):
        """Store allocation in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO strategy_allocations 
                (timestamp, allocations, allocation_method, market_regime, portfolio_volatility)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                allocation.timestamp,
                json.dumps({k.value: v for k, v in allocation.allocations.items()}),
                allocation.allocation_method.value,
                allocation.market_regime.value,
                allocation.portfolio_volatility
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing allocation: {e}")
    
    def get_framework_summary(self) -> Dict[str, Any]:
        """Get comprehensive framework summary"""
        try:
            # Strategy summaries
            strategy_summaries = {}
            for strategy_type, strategy in self.strategies.items():
                recent_performance = strategy.performance_history[-30:] if len(strategy.performance_history) >= 30 else strategy.performance_history
                
                strategy_summaries[strategy_type.value] = {
                    'current_allocation': self.current_allocation.allocations.get(strategy_type, 0.0),
                    'recent_sharpe': strategy.get_sharpe_ratio(30),
                    'total_signals': len(strategy.signal_history),
                    'performance_records': len(strategy.performance_history),
                    'avg_recent_return': np.mean([p.total_return for p in recent_performance]) if recent_performance else 0.0
                }
            
            return {
                'active_strategies': len(self.strategies),
                'current_market_regime': self.current_market_regime.value,
                'current_allocation': {k.value: v for k, v in self.current_allocation.allocations.items()},
                'allocation_method': self.current_allocation.allocation_method.value,
                'portfolio_volatility': self.current_allocation.portfolio_volatility,
                'portfolio_var': self.current_allocation.portfolio_var,
                'diversification_ratio': self.current_allocation.diversification_ratio,
                'strategy_summaries': strategy_summaries,
                'regime_changes': len(self.regime_history),
                'allocation_updates': len(self.allocation_history),
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating framework summary: {e}")
            return {}

# Example usage
if __name__ == "__main__":
    # Configuration for multi-strategy framework
    config = {
        'strategies': {
            'statistical_arbitrage': {
                'lookback_period': 252,
                'correlation_threshold': 0.7,
                'entry_zscore': 2.0,
                'exit_zscore': 0.5,
                'max_position_size': 0.1,
                'pairs_universe': [
                    ('PAIR_1', {'symbol1': 'AAPL', 'symbol2': 'MSFT'}),
                    ('PAIR_2', {'symbol1': 'GOOGL', 'symbol2': 'META'})
                ]
            },
            'momentum': {
                'momentum_lookback': 20,
                'momentum_threshold': 0.02,
                'trend_strength_threshold': 0.6,
                'max_position_size': 0.15,
                'use_rsi': True,
                'use_macd': True
            },
            'mean_reversion': {
                'reversion_lookback': 20,
                'deviation_threshold': 2.0,
                'mean_reversion_strength_threshold': 0.6,
                'max_position_size': 0.12
            },
            'volatility': {
                'vol_lookback': 20,
                'vol_threshold': 0.02,
                'max_position_size': 0.08,
                'use_vix': True
            }
        },
        'db_path': 'multi_strategy_framework.db'
    }
    
    # Create framework
    framework = MultiStrategyFramework(config)
    
    # Generate sample market data
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'META', 'SPY', 'VIX']
    
    # Generate random price data
    np.random.seed(42)
    market_data = pd.DataFrame(index=dates)
    
    for symbol in symbols:
        # Generate price series with some correlation structure
        returns = np.random.normal(0.0005, 0.02, len(dates))
        if symbol == 'VIX':
            returns = np.random.normal(0, 0.05, len(dates))  # More volatile for VIX
        
        prices = [100]  # Starting price
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        market_data[symbol] = prices[1:]
    
    # Update market regime
    framework.update_market_regime(market_data)
    
    # Generate signals from all strategies
    all_signals = framework.generate_all_signals(market_data.tail(100))
    
    print("Generated signals:")
    for strategy_type, signals in all_signals.items():
        print(f"{strategy_type.value}: {len(signals)} signals")
        for signal in signals[:3]:  # Show first 3 signals
            print(f"  {signal.symbol}: {signal.signal_strength:.3f} (confidence: {signal.confidence:.3f})")
    
    # Update allocation
    framework.update_allocation(AllocationMethod.RISK_PARITY)
    
    # Get framework summary
    summary = framework.get_framework_summary()
    print(f"\nFramework Summary:")
    print(json.dumps(summary, indent=2)) 