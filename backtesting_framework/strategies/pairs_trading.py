"""
Pairs Trading Strategy

Statistical arbitrage strategy based on mean reversion of price spreads
between correlated assets.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from scipy import stats
from sklearn.linear_model import LinearRegression

from dataclasses import dataclass
from .base_strategy import BaseStrategy, StrategyConfig, TradingSignal, SignalType, Position

logger = logging.getLogger(__name__)

@dataclass
class PairsTradingConfig(StrategyConfig):
    """Configuration specific to pairs trading strategy"""
    # Pairs trading parameters
    z_entry_threshold: float = 2.0
    z_exit_threshold: float = 0.5
    lookback_window: int = 60
    correlation_threshold: float = 0.8
    cointegration_pvalue: float = 0.05
    
    # Position sizing
    position_size: float = 0.2
    max_positions: int = 5
    
    # Risk management
    stop_loss: Optional[float] = 0.05
    take_profit: Optional[float] = 0.02
    max_drawdown: float = 0.15

class PairsTradingStrategy(BaseStrategy):
    """
    Pairs Trading Strategy
    
    Implements statistical arbitrage based on mean reversion of price spreads
    between correlated assets. Uses z-score based entry/exit signals.
    """
    
    def __init__(self, config: PairsTradingConfig):
        """
        Initialize pairs trading strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy-specific state
        self.spread_history: List[float] = []
        self.z_scores: List[float] = []
        self.hedge_ratio: Optional[float] = None
        self.spread_mean: Optional[float] = None
        self.spread_std: Optional[float] = None
        
        # Pair information
        if len(config.symbols) != 2:
            raise ValueError("Pairs trading requires exactly 2 symbols")
        
        self.symbol1 = config.symbols[0]
        self.symbol2 = config.symbols[1]
        
        logger.info(f"Initialized pairs trading strategy: {self.symbol1} vs {self.symbol2}")
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Generate trading signals based on spread z-score
        
        Args:
            data: Dictionary mapping symbols to DataFrames
            
        Returns:
            List of trading signals
        """
        signals = []
        
        # Check if we have data for both symbols
        if self.symbol1 not in data or self.symbol2 not in data:
            return signals
        
        # Get latest prices
        price1 = data[self.symbol1]['close'].iloc[-1]
        price2 = data[self.symbol2]['close'].iloc[-1]
        
        # Calculate spread
        if self.hedge_ratio is None:
            # Initialize hedge ratio using linear regression
            self._calculate_hedge_ratio(data)
        
        if self.hedge_ratio is None:
            return signals
        
        spread = price1 - self.hedge_ratio * price2
        self.spread_history.append(spread)
        
        # Calculate z-score
        z_score = self._calculate_z_score()
        self.z_scores.append(z_score)
        
        # Generate signals based on z-score
        if z_score > self.config.z_entry_threshold:
            # Spread is too high - short symbol1, long symbol2
            signals.append(TradingSignal(
                timestamp=datetime.now(),
                symbol=self.symbol1,
                signal_type=SignalType.SHORT,
                strength=min(abs(z_score) / 4.0, 1.0),
                confidence=0.8,
                price=price1,
                metadata={'z_score': z_score, 'spread': spread}
            ))
            
            signals.append(TradingSignal(
                timestamp=datetime.now(),
                symbol=self.symbol2,
                signal_type=SignalType.LONG,
                strength=min(abs(z_score) / 4.0, 1.0),
                confidence=0.8,
                price=price2,
                metadata={'z_score': z_score, 'spread': spread}
            ))
            
        elif z_score < -self.config.z_entry_threshold:
            # Spread is too low - long symbol1, short symbol2
            signals.append(TradingSignal(
                timestamp=datetime.now(),
                symbol=self.symbol1,
                signal_type=SignalType.LONG,
                strength=min(abs(z_score) / 4.0, 1.0),
                confidence=0.8,
                price=price1,
                metadata={'z_score': z_score, 'spread': spread}
            ))
            
            signals.append(TradingSignal(
                timestamp=datetime.now(),
                symbol=self.symbol2,
                signal_type=SignalType.SHORT,
                strength=min(abs(z_score) / 4.0, 1.0),
                confidence=0.8,
                price=price2,
                metadata={'z_score': z_score, 'spread': spread}
            ))
            
        elif abs(z_score) < self.config.z_exit_threshold:
            # Spread is near mean - close positions
            if self.symbol1 in self.positions:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    symbol=self.symbol1,
                    signal_type=SignalType.CLOSE_LONG if self.positions[self.symbol1].quantity > 0 else SignalType.CLOSE_SHORT,
                    strength=0.5,
                    confidence=0.7,
                    price=price1,
                    metadata={'z_score': z_score, 'spread': spread}
                ))
            
            if self.symbol2 in self.positions:
                signals.append(TradingSignal(
                    timestamp=datetime.now(),
                    symbol=self.symbol2,
                    signal_type=SignalType.CLOSE_LONG if self.positions[self.symbol2].quantity > 0 else SignalType.CLOSE_SHORT,
                    strength=0.5,
                    confidence=0.7,
                    price=price2,
                    metadata={'z_score': z_score, 'spread': spread}
                ))
        
        return signals
    
    def calculate_positions(self, signals: List[TradingSignal], 
                          current_positions: Dict[str, Position],
                          available_cash: float) -> Dict[str, float]:
        """
        Calculate target positions based on signals
        
        Args:
            signals: List of trading signals
            current_positions: Current portfolio positions
            available_cash: Available cash for trading
            
        Returns:
            Dictionary mapping symbols to target position sizes
        """
        target_positions = {}
        
        # Process signals
        for signal in signals:
            if signal.signal_type in [SignalType.LONG, SignalType.SHORT]:
                # Calculate position size based on signal strength and available cash
                position_value = available_cash * self.config.position_size * signal.strength
                position_size = position_value / signal.price
                
                if signal.signal_type == SignalType.SHORT:
                    position_size = -position_size
                
                target_positions[signal.symbol] = position_size
                
            elif signal.signal_type in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
                # Close position
                target_positions[signal.symbol] = 0.0
        
        return target_positions
    
    def _calculate_hedge_ratio(self, data: Dict[str, pd.DataFrame]):
        """
        Calculate hedge ratio using linear regression
        
        Args:
            data: Market data for both symbols
        """
        if len(data[self.symbol1]) < self.config.lookback_window:
            return
        
        # Get price series
        prices1 = data[self.symbol1]['close'].tail(self.config.lookback_window)
        prices2 = data[self.symbol2]['close'].tail(self.config.lookback_window)
        
        # Check correlation
        correlation = prices1.corr(prices2)
        if abs(correlation) < self.config.correlation_threshold:
            logger.warning(f"Low correlation between {self.symbol1} and {self.symbol2}: {correlation:.3f}")
            return
        
        # Calculate hedge ratio using linear regression
        try:
            model = LinearRegression()
            model.fit(prices2.values.reshape(-1, 1), prices1.values)
            self.hedge_ratio = model.coef_[0]
            
            logger.info(f"Hedge ratio calculated: {self.hedge_ratio:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to calculate hedge ratio: {e}")
            self.hedge_ratio = None
    
    def _calculate_z_score(self) -> float:
        """
        Calculate z-score of current spread
        
        Returns:
            Z-score value
        """
        if len(self.spread_history) < self.config.lookback_window:
            return 0.0
        
        # Use rolling window for mean and std
        recent_spreads = self.spread_history[-self.config.lookback_window:]
        spread_mean = np.mean(recent_spreads)
        spread_std = np.std(recent_spreads)
        
        if spread_std == 0:
            return 0.0
        
        current_spread = self.spread_history[-1]
        z_score = (current_spread - spread_mean) / spread_std
        
        return z_score
    
    def generate_features(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Generate features for the strategy
        
        Args:
            data: Market data
            
        Returns:
            Dictionary of feature DataFrames
        """
        features = {}
        
        for symbol, df in data.items():
            # Technical indicators
            features[symbol] = pd.DataFrame(index=df.index)
            
            # Returns
            features[symbol]['returns'] = df['close'].pct_change()
            
            # Moving averages
            features[symbol]['ma_20'] = df['close'].rolling(20).mean()
            features[symbol]['ma_50'] = df['close'].rolling(50).mean()
            
            # Volatility
            features[symbol]['volatility'] = features[symbol]['returns'].rolling(20).std()
            
            # RSI
            features[symbol]['rsi'] = self._calculate_rsi(df['close'])
        
        return features
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """
        Get strategy-specific metrics
        
        Returns:
            Dictionary of strategy metrics
        """
        metrics = super().get_performance_metrics()
        
        # Add pairs trading specific metrics
        if len(self.z_scores) > 0:
            metrics.update({
                'avg_z_score': np.mean(self.z_scores),
                'z_score_volatility': np.std(self.z_scores),
                'max_z_score': np.max(self.z_scores),
                'min_z_score': np.min(self.z_scores),
                'hedge_ratio': self.hedge_ratio,
                'spread_mean': np.mean(self.spread_history) if self.spread_history else 0,
                'spread_std': np.std(self.spread_history) if self.spread_history else 0
            })
        
        return metrics
    
    def reset(self):
        """Reset strategy state"""
        super().reset()
        
        # Reset strategy-specific state
        self.spread_history.clear()
        self.z_scores.clear()
        self.hedge_ratio = None
        self.spread_mean = None
        self.spread_std = None
        
        logger.info("Pairs trading strategy reset") 