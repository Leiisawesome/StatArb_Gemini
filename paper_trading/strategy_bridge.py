"""
Strategy Bridge for Paper Trading
================================

Bridges backtesting strategies to live trading environment.
Converts backtest logic to real-time signal generation and execution.

Features:
- Real-time signal generation from backtest strategies
- Live market data integration
- Position management and tracking
- Risk control integration
- Performance monitoring

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

# Import core components
from core_structure.components.broker_integration import IBKRClient, IBKRConfig
from core_structure.components.broker_integration.base_broker import (
    Order, OrderType, OrderSide, OrderStatus, MarketData, Position
)

# Import configuration
from .config.paper_trading_config_manager import (
    PaperTradingConfigManager, LiveStrategyConfig, TradingEnvironment
)

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"

@dataclass
class LiveTradingSignal:
    """Live trading signal"""
    symbol: str
    signal_type: SignalType
    confidence: float
    target_position_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategyState:
    """Current state of a strategy"""
    strategy_id: str
    is_active: bool = True
    current_positions: Dict[str, float] = field(default_factory=dict)
    pending_orders: Dict[str, str] = field(default_factory=dict)  # symbol -> order_id
    last_signal_time: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)

class BaseStrategyBridge(ABC):
    """
    Abstract base class for strategy bridges
    
    Each strategy (momentum, mean reversion, pairs trading) will have
    its own bridge implementation that converts backtest logic to live trading.
    """
    
    def __init__(self, strategy_config: LiveStrategyConfig, 
                 broker_client: IBKRClient,
                 config_manager: PaperTradingConfigManager):
        """
        Initialize strategy bridge
        
        Args:
            strategy_config: Live strategy configuration
            broker_client: IBKR client for market data and execution
            config_manager: Paper trading configuration manager
        """
        self.strategy_config = strategy_config
        self.broker_client = broker_client
        self.config_manager = config_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Strategy state
        self.state = StrategyState(strategy_id=strategy_config.strategy_id)
        
        # Market data cache
        self.market_data_cache: Dict[str, MarketData] = {}
        self.historical_data_cache: Dict[str, pd.DataFrame] = {}
        
        # Signal generation
        self.last_signal_generation = None
        self.signal_frequency_seconds = self._parse_frequency(strategy_config.signal_frequency)
        
        # Performance tracking
        self.start_time = datetime.now()
        self.total_pnl = 0.0
        self.trade_count = 0
        self.winning_trades = 0
        
        self.logger.info(f"✅ Strategy bridge initialized: {strategy_config.strategy_id}")
    
    def _parse_frequency(self, frequency: str) -> int:
        """Parse frequency string to seconds"""
        freq_map = {
            '1min': 60,
            '5min': 300,
            '15min': 900,
            '1h': 3600,
            '1d': 86400
        }
        return freq_map.get(frequency, 60)
    
    @abstractmethod
    async def generate_signals(self, symbols: List[str]) -> List[LiveTradingSignal]:
        """
        Generate trading signals for given symbols
        
        This method should implement the strategy-specific logic
        converted from the backtest implementation.
        """
        pass
    
    @abstractmethod
    async def update_positions(self, current_positions: Dict[str, Position]) -> None:
        """Update strategy state with current positions"""
        pass
    
    @abstractmethod
    async def calculate_position_size(self, signal: LiveTradingSignal, 
                                    available_capital: float) -> float:
        """Calculate appropriate position size for a signal"""
        pass
    
    async def get_market_data(self, symbol: str, force_refresh: bool = False) -> MarketData:
        """Get current market data for symbol"""
        try:
            # Check cache first
            if not force_refresh and symbol in self.market_data_cache:
                cached_data = self.market_data_cache[symbol]
                # Use cached data if less than 30 seconds old
                if (datetime.now() - cached_data.timestamp).total_seconds() < 30:
                    return cached_data
            
            # Fetch fresh data
            market_data = await self.broker_client.get_market_data(symbol)
            self.market_data_cache[symbol] = market_data
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get market data for {symbol}: {e}")
            # Return cached data if available, otherwise create dummy data
            if symbol in self.market_data_cache:
                return self.market_data_cache[symbol]
            else:
                return MarketData(symbol=symbol, bid=0.0, ask=0.0, last=0.0, volume=0)
    
    async def get_historical_data(self, symbol: str, periods: int = 100, 
                                frequency: str = "1min") -> pd.DataFrame:
        """Get historical data for technical analysis"""
        try:
            cache_key = f"{symbol}_{periods}_{frequency}"
            
            # Check cache
            if cache_key in self.historical_data_cache:
                cached_df = self.historical_data_cache[cache_key]
                # Use cached data if less than 5 minutes old
                if len(cached_df) > 0:
                    last_timestamp = pd.to_datetime(cached_df.index[-1])
                    if (datetime.now() - last_timestamp).total_seconds() < 300:
                        return cached_df
            
            # Fetch historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=max(periods // 390 + 1, 5))  # Estimate trading days
            
            historical_data = await self.broker_client.get_historical_data(
                symbol, start_date, end_date
            )
            
            # Convert to DataFrame
            if historical_data:
                df = pd.DataFrame([{
                    'timestamp': data.timestamp,
                    'open': data.open or data.last,
                    'high': data.high or data.last,
                    'low': data.low or data.last,
                    'close': data.close or data.last,
                    'volume': data.volume
                } for data in historical_data])
                
                df.set_index('timestamp', inplace=True)
                df = df.tail(periods)  # Keep only requested periods
                
                # Cache the data
                self.historical_data_cache[cache_key] = df
                
                return df
            else:
                # Return empty DataFrame if no data
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    async def should_generate_signals(self) -> bool:
        """Check if it's time to generate new signals"""
        if self.last_signal_generation is None:
            return True
        
        time_since_last = (datetime.now() - self.last_signal_generation).total_seconds()
        return time_since_last >= self.signal_frequency_seconds
    
    async def update_performance_metrics(self, current_positions: Dict[str, Position]) -> None:
        """Update strategy performance metrics"""
        try:
            # Calculate current portfolio value
            portfolio_value = 0.0
            unrealized_pnl = 0.0
            
            for symbol, position in current_positions.items():
                portfolio_value += position.market_value
                unrealized_pnl += position.unrealized_pnl
            
            # Calculate performance metrics
            total_pnl = self.total_pnl + unrealized_pnl
            
            # Calculate time-based metrics
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            elapsed_days = elapsed_time / 86400
            
            # Update metrics
            self.state.performance_metrics.update({
                'total_pnl': total_pnl,
                'unrealized_pnl': unrealized_pnl,
                'realized_pnl': self.total_pnl,
                'portfolio_value': portfolio_value,
                'trade_count': self.trade_count,
                'win_rate': self.winning_trades / max(self.trade_count, 1),
                'elapsed_days': elapsed_days,
                'daily_pnl': total_pnl / max(elapsed_days, 1/24)  # Minimum 1 hour
            })
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update performance metrics: {e}")
    
    def get_strategy_state(self) -> StrategyState:
        """Get current strategy state"""
        return self.state
    
    def set_active(self, active: bool) -> None:
        """Enable or disable strategy"""
        self.state.is_active = active
        status = "enabled" if active else "disabled"
        self.logger.info(f"📊 Strategy {self.strategy_config.strategy_id} {status}")

class MomentumStrategyBridge(BaseStrategyBridge):
    """
    Momentum strategy bridge
    
    Converts the advanced momentum backtest strategy to live trading.
    Implements real-time momentum calculation and signal generation.
    """
    
    def __init__(self, strategy_config: LiveStrategyConfig, 
                 broker_client: IBKRClient,
                 config_manager: PaperTradingConfigManager):
        super().__init__(strategy_config, broker_client, config_manager)
        
        # Momentum-specific parameters
        self.lookback_periods = [20, 50, 100]  # Multi-period momentum
        self.momentum_threshold = 0.015  # 1.5% momentum threshold
        self.atr_multiplier = 2.0  # ATR-based stops
        self.trend_lookback = 50
        
        self.logger.info("🚀 Momentum strategy bridge initialized")
    
    async def generate_signals(self, symbols: List[str]) -> List[LiveTradingSignal]:
        """Generate momentum-based trading signals"""
        signals = []
        
        try:
            for symbol in symbols:
                # Get historical data for momentum calculation
                df = await self.get_historical_data(symbol, periods=max(self.lookback_periods) + 20)
                
                if len(df) < max(self.lookback_periods):
                    self.logger.warning(f"⚠️  Insufficient data for {symbol}")
                    continue
                
                # Calculate momentum signals
                signal = await self._calculate_momentum_signal(symbol, df)
                if signal:
                    signals.append(signal)
            
            self.last_signal_generation = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate momentum signals: {e}")
        
        return signals
    
    async def _calculate_momentum_signal(self, symbol: str, df: pd.DataFrame) -> Optional[LiveTradingSignal]:
        """Calculate momentum signal for a symbol"""
        try:
            # Calculate returns for different periods
            momentum_scores = []
            
            for period in self.lookback_periods:
                if len(df) >= period:
                    returns = df['close'].pct_change(period).iloc[-1]
                    momentum_scores.append(returns)
            
            if not momentum_scores:
                return None
            
            # Weighted momentum score (shorter periods get higher weight)
            weights = [0.5, 0.3, 0.2]  # 20-period gets 50%, 50-period gets 30%, 100-period gets 20%
            weighted_momentum = sum(score * weight for score, weight in zip(momentum_scores, weights))
            
            # Calculate ATR for stop-loss
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            atr = df['tr'].rolling(window=14).mean().iloc[-1]
            
            # Generate signal
            current_price = df['close'].iloc[-1]
            
            if weighted_momentum > self.momentum_threshold:
                # Strong positive momentum - BUY signal
                return LiveTradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=min(abs(weighted_momentum) / self.momentum_threshold, 1.0),
                    target_position_size=self._calculate_momentum_position_size(weighted_momentum),
                    stop_loss=current_price - (atr * self.atr_multiplier),
                    take_profit=current_price + (atr * self.atr_multiplier * 1.5),
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'momentum_score': weighted_momentum,
                        'atr': atr,
                        'lookback_scores': momentum_scores
                    }
                )
            elif weighted_momentum < -self.momentum_threshold:
                # Strong negative momentum - SELL signal
                return LiveTradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    confidence=min(abs(weighted_momentum) / self.momentum_threshold, 1.0),
                    target_position_size=self._calculate_momentum_position_size(abs(weighted_momentum)),
                    stop_loss=current_price + (atr * self.atr_multiplier),
                    take_profit=current_price - (atr * self.atr_multiplier * 1.5),
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'momentum_score': weighted_momentum,
                        'atr': atr,
                        'lookback_scores': momentum_scores
                    }
                )
            
            return None  # No signal if momentum is weak
            
        except Exception as e:
            self.logger.error(f"❌ Failed to calculate momentum signal for {symbol}: {e}")
            return None
    
    def _calculate_momentum_position_size(self, momentum_score: float) -> float:
        """Calculate position size based on momentum strength"""
        # Base position size from configuration
        base_size = 1.0 / self.strategy_config.max_positions
        
        # Scale by momentum strength (max 1.5x base size)
        momentum_multiplier = 1.0 + min(abs(momentum_score) / self.momentum_threshold * 0.5, 0.5)
        
        return base_size * momentum_multiplier
    
    async def update_positions(self, current_positions: Dict[str, Position]) -> None:
        """Update momentum strategy positions"""
        self.state.current_positions = {
            symbol: pos.quantity for symbol, pos in current_positions.items()
        }
        await self.update_performance_metrics(current_positions)
    
    async def calculate_position_size(self, signal: LiveTradingSignal, 
                                    available_capital: float) -> float:
        """Calculate position size for momentum signal"""
        # Get target allocation from signal
        target_allocation = signal.target_position_size
        
        # Apply risk limits
        max_position_value = available_capital * target_allocation
        
        # Get current price
        market_data = await self.get_market_data(signal.symbol)
        current_price = market_data.last or market_data.bid or market_data.ask
        
        if current_price <= 0:
            return 0.0
        
        # Calculate shares
        shares = max_position_value / current_price
        
        # Apply minimum position size
        min_shares = 1000 / current_price  # Minimum $1000 position
        
        return max(shares, min_shares)

class MeanReversionStrategyBridge(BaseStrategyBridge):
    """
    Mean reversion strategy bridge
    
    Converts the advanced mean reversion backtest strategy to live trading.
    Implements real-time z-score calculation and mean reversion signals.
    """
    
    def __init__(self, strategy_config: LiveStrategyConfig, 
                 broker_client: IBKRClient,
                 config_manager: PaperTradingConfigManager):
        super().__init__(strategy_config, broker_client, config_manager)
        
        # Mean reversion parameters
        self.lookback_window = 252  # 1 year of data
        self.entry_zscore_threshold = 2.0
        self.exit_zscore_threshold = 0.5
        self.stop_loss_zscore = 3.0
        
        self.logger.info("📈 Mean reversion strategy bridge initialized")
    
    async def generate_signals(self, symbols: List[str]) -> List[LiveTradingSignal]:
        """Generate mean reversion signals"""
        signals = []
        
        try:
            for symbol in symbols:
                # Get historical data for z-score calculation
                df = await self.get_historical_data(symbol, periods=self.lookback_window + 50)
                
                if len(df) < self.lookback_window:
                    self.logger.warning(f"⚠️  Insufficient data for {symbol}")
                    continue
                
                # Calculate mean reversion signal
                signal = await self._calculate_mean_reversion_signal(symbol, df)
                if signal:
                    signals.append(signal)
            
            self.last_signal_generation = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate mean reversion signals: {e}")
        
        return signals
    
    async def _calculate_mean_reversion_signal(self, symbol: str, df: pd.DataFrame) -> Optional[LiveTradingSignal]:
        """Calculate mean reversion signal using z-score"""
        try:
            # Calculate rolling statistics
            rolling_mean = df['close'].rolling(window=self.lookback_window).mean()
            rolling_std = df['close'].rolling(window=self.lookback_window).std()
            
            # Calculate z-score
            current_price = df['close'].iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            current_std = rolling_std.iloc[-1]
            
            if current_std == 0:
                return None
            
            zscore = (current_price - current_mean) / current_std
            
            # Generate signals based on z-score
            if zscore > self.entry_zscore_threshold:
                # Price is too high - SELL signal (expect reversion down)
                return LiveTradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_mean_reversion_position_size(abs(zscore)),
                    stop_loss=current_price + (current_std * self.stop_loss_zscore),
                    take_profit=current_mean,  # Target mean reversion
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'zscore': zscore,
                        'mean': current_mean,
                        'std': current_std,
                        'lookback_window': self.lookback_window
                    }
                )
            elif zscore < -self.entry_zscore_threshold:
                # Price is too low - BUY signal (expect reversion up)
                return LiveTradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_mean_reversion_position_size(abs(zscore)),
                    stop_loss=current_price - (current_std * self.stop_loss_zscore),
                    take_profit=current_mean,  # Target mean reversion
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'zscore': zscore,
                        'mean': current_mean,
                        'std': current_std,
                        'lookback_window': self.lookback_window
                    }
                )
            elif abs(zscore) < self.exit_zscore_threshold:
                # Price near mean - EXIT signal for existing positions
                return LiveTradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.EXIT,
                    confidence=1.0 - abs(zscore) / self.exit_zscore_threshold,
                    target_position_size=0.0,
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'zscore': zscore,
                        'exit_reason': 'mean_reversion_target_reached'
                    }
                )
            
            return None  # No signal
            
        except Exception as e:
            self.logger.error(f"❌ Failed to calculate mean reversion signal for {symbol}: {e}")
            return None
    
    def _calculate_mean_reversion_position_size(self, zscore_magnitude: float) -> float:
        """Calculate position size based on z-score magnitude"""
        # Base position size
        base_size = 1.0 / self.strategy_config.max_positions
        
        # Scale by z-score strength (higher z-score = larger position)
        zscore_multiplier = 1.0 + min((zscore_magnitude - self.entry_zscore_threshold) * 0.3, 0.5)
        
        return base_size * zscore_multiplier
    
    async def update_positions(self, current_positions: Dict[str, Position]) -> None:
        """Update mean reversion strategy positions"""
        self.state.current_positions = {
            symbol: pos.quantity for symbol, pos in current_positions.items()
        }
        await self.update_performance_metrics(current_positions)
    
    async def calculate_position_size(self, signal: LiveTradingSignal, 
                                    available_capital: float) -> float:
        """Calculate position size for mean reversion signal"""
        # Get target allocation from signal
        target_allocation = signal.target_position_size
        
        # Apply risk limits
        max_position_value = available_capital * target_allocation
        
        # Get current price
        market_data = await self.get_market_data(signal.symbol)
        current_price = market_data.last or market_data.bid or market_data.ask
        
        if current_price <= 0:
            return 0.0
        
        # Calculate shares
        shares = max_position_value / current_price
        
        # Apply minimum position size
        min_shares = 1000 / current_price  # Minimum $1000 position
        
        return max(shares, min_shares)

class PairsTradingStrategyBridge(BaseStrategyBridge):
    """
    Pairs trading strategy bridge
    
    Converts the pairs trading backtest strategy to live trading.
    Implements real-time cointegration monitoring and spread trading.
    """
    
    def __init__(self, strategy_config: LiveStrategyConfig, 
                 broker_client: IBKRClient,
                 config_manager: PaperTradingConfigManager):
        super().__init__(strategy_config, broker_client, config_manager)
        
        # Pairs trading parameters
        self.lookback_window = 252
        self.entry_zscore_threshold = 1.0  # More sensitive for pairs
        self.exit_zscore_threshold = 0.5
        self.cointegration_threshold = 0.05
        
        # Default pairs (can be configured)
        self.trading_pairs = [("GLD", "GDX"), ("AAPL", "MSFT")]
        
        self.logger.info("⚖️  Pairs trading strategy bridge initialized")
    
    async def generate_signals(self, symbols: List[str]) -> List[LiveTradingSignal]:
        """Generate pairs trading signals"""
        signals = []
        
        try:
            # Generate signals for each pair
            for symbol1, symbol2 in self.trading_pairs:
                if symbol1 in symbols or symbol2 in symbols:
                    pair_signals = await self._calculate_pairs_signals(symbol1, symbol2)
                    signals.extend(pair_signals)
            
            self.last_signal_generation = datetime.now()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate pairs trading signals: {e}")
        
        return signals
    
    async def _calculate_pairs_signals(self, symbol1: str, symbol2: str) -> List[LiveTradingSignal]:
        """Calculate pairs trading signals for a pair"""
        try:
            # Get historical data for both symbols
            df1 = await self.get_historical_data(symbol1, periods=self.lookback_window + 50)
            df2 = await self.get_historical_data(symbol2, periods=self.lookback_window + 50)
            
            if len(df1) < self.lookback_window or len(df2) < self.lookback_window:
                self.logger.warning(f"⚠️  Insufficient data for pair {symbol1}/{symbol2}")
                return []
            
            # Align data by timestamp
            aligned_data = pd.concat([df1['close'], df2['close']], axis=1, keys=[symbol1, symbol2])
            aligned_data.dropna(inplace=True)
            
            if len(aligned_data) < self.lookback_window:
                return []
            
            # Calculate spread and z-score
            price1 = aligned_data[symbol1].iloc[-1]
            price2 = aligned_data[symbol2].iloc[-1]
            
            # Simple hedge ratio (can be enhanced with cointegration)
            hedge_ratio = aligned_data[symbol1].corr(aligned_data[symbol2])
            
            # Calculate spread
            spread = aligned_data[symbol1] - hedge_ratio * aligned_data[symbol2]
            spread_mean = spread.rolling(window=self.lookback_window).mean().iloc[-1]
            spread_std = spread.rolling(window=self.lookback_window).std().iloc[-1]
            
            if spread_std == 0:
                return []
            
            current_spread = price1 - hedge_ratio * price2
            zscore = (current_spread - spread_mean) / spread_std
            
            signals = []
            
            # Generate pair signals based on z-score
            if zscore > self.entry_zscore_threshold:
                # Spread is too high - SELL symbol1, BUY symbol2
                signals.append(LiveTradingSignal(
                    symbol=symbol1,
                    signal_type=SignalType.SELL,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_pairs_position_size(abs(zscore)),
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'pair_symbol': symbol2,
                        'zscore': zscore,
                        'hedge_ratio': hedge_ratio,
                        'spread': current_spread,
                        'pair_trade': True
                    }
                ))
                
                signals.append(LiveTradingSignal(
                    symbol=symbol2,
                    signal_type=SignalType.BUY,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_pairs_position_size(abs(zscore)) * hedge_ratio,
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'pair_symbol': symbol1,
                        'zscore': zscore,
                        'hedge_ratio': hedge_ratio,
                        'spread': current_spread,
                        'pair_trade': True
                    }
                ))
                
            elif zscore < -self.entry_zscore_threshold:
                # Spread is too low - BUY symbol1, SELL symbol2
                signals.append(LiveTradingSignal(
                    symbol=symbol1,
                    signal_type=SignalType.BUY,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_pairs_position_size(abs(zscore)),
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'pair_symbol': symbol2,
                        'zscore': zscore,
                        'hedge_ratio': hedge_ratio,
                        'spread': current_spread,
                        'pair_trade': True
                    }
                ))
                
                signals.append(LiveTradingSignal(
                    symbol=symbol2,
                    signal_type=SignalType.SELL,
                    confidence=min(abs(zscore) / self.entry_zscore_threshold, 1.0),
                    target_position_size=self._calculate_pairs_position_size(abs(zscore)) * hedge_ratio,
                    strategy_id=self.strategy_config.strategy_id,
                    metadata={
                        'pair_symbol': symbol1,
                        'zscore': zscore,
                        'hedge_ratio': hedge_ratio,
                        'spread': current_spread,
                        'pair_trade': True
                    }
                ))
            
            elif abs(zscore) < self.exit_zscore_threshold:
                # Spread converged - EXIT both positions
                for symbol in [symbol1, symbol2]:
                    signals.append(LiveTradingSignal(
                        symbol=symbol,
                        signal_type=SignalType.EXIT,
                        confidence=1.0 - abs(zscore) / self.exit_zscore_threshold,
                        target_position_size=0.0,
                        strategy_id=self.strategy_config.strategy_id,
                        metadata={
                            'zscore': zscore,
                            'exit_reason': 'spread_convergence',
                            'pair_trade': True
                        }
                    ))
            
            return signals
            
        except Exception as e:
            self.logger.error(f"❌ Failed to calculate pairs signals for {symbol1}/{symbol2}: {e}")
            return []
    
    def _calculate_pairs_position_size(self, zscore_magnitude: float) -> float:
        """Calculate position size for pairs trading"""
        # Base position size (pairs use smaller positions due to market neutrality)
        base_size = 1.0 / (self.strategy_config.max_positions * 2)  # Each pair uses 2 positions
        
        # Scale by z-score strength
        zscore_multiplier = 1.0 + min((zscore_magnitude - self.entry_zscore_threshold) * 0.2, 0.3)
        
        return base_size * zscore_multiplier
    
    async def update_positions(self, current_positions: Dict[str, Position]) -> None:
        """Update pairs trading strategy positions"""
        self.state.current_positions = {
            symbol: pos.quantity for symbol, pos in current_positions.items()
        }
        await self.update_performance_metrics(current_positions)
    
    async def calculate_position_size(self, signal: LiveTradingSignal, 
                                    available_capital: float) -> float:
        """Calculate position size for pairs trading signal"""
        # Get target allocation from signal
        target_allocation = signal.target_position_size
        
        # For pairs trading, use smaller position sizes due to market neutrality
        max_position_value = available_capital * target_allocation * 0.5  # 50% of normal size
        
        # Get current price
        market_data = await self.get_market_data(signal.symbol)
        current_price = market_data.last or market_data.bid or market_data.ask
        
        if current_price <= 0:
            return 0.0
        
        # Calculate shares
        shares = max_position_value / current_price
        
        # Apply minimum position size
        min_shares = 500 / current_price  # Minimum $500 position for pairs
        
        return max(shares, min_shares)

class StrategyBridgeFactory:
    """Factory for creating strategy bridges"""
    
    @staticmethod
    def create_bridge(strategy_type: str, strategy_config: LiveStrategyConfig,
                     broker_client: IBKRClient, 
                     config_manager: PaperTradingConfigManager) -> BaseStrategyBridge:
        """Create appropriate strategy bridge"""
        
        bridge_map = {
            'momentum': MomentumStrategyBridge,
            'mean_reversion': MeanReversionStrategyBridge,
            'pairs_trading': PairsTradingStrategyBridge
        }
        
        if strategy_type not in bridge_map:
            raise ValueError(f"Unsupported strategy type: {strategy_type}")
        
        bridge_class = bridge_map[strategy_type]
        return bridge_class(strategy_config, broker_client, config_manager)
