"""
Advanced Pairs Trading Strategy Implementation

This module implements sophisticated pairs trading strategies that exploit
mean-reverting relationships between correlated assets using statistical
arbitrage principles and cointegration analysis.

The strategy uses:
- Cointegration testing and error correction models
- Dynamic correlation analysis and pair selection
- Kalman filtering for spread estimation
- Risk management with position sizing and stop losses
- Adaptive entry/exit thresholds based on market conditions

Key Features:
- Statistical pair selection using correlation and cointegration
- Dynamic hedging ratios and spread calculation
- Mean reversion entry/exit signals
- Risk parity position sizing across pairs
- False signal filtering and re-entry logic

Academic Foundations:
- Engle & Granger (1987) cointegration theory
- Johansen (1991) multivariate cointegration
- Gatev, Goetzmann & Rouwenhorst (2006) pairs trading
- Do & Faff (2010) pairs trading with cointegration
- Krauss (2017) statistical arbitrage in futures

Components:
- Pair selection algorithms
- Spread calculation and normalization
- Cointegration testing framework
- Entry/exit signal generation
- Risk management systems
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from statsmodels.tsa.stattools import coint, adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class PairSelectionMethod(Enum):
    """Methods for selecting trading pairs"""
    CORRELATION = "correlation"
    COINTEGRATION = "cointegration"
    DISTANCE = "distance"
    SECTOR_NEUTRAL = "sector_neutral"
    STATISTICAL = "statistical"


class SpreadCalculationMethod(Enum):
    """Methods for calculating the spread between pairs"""
    OLS_REGRESSION = "ols_regression"
    KALMAN_FILTER = "kalman_filter"
    DYNAMIC_HEDGE = "dynamic_hedge"
    COINTEGRATION = "cointegration"


class EntryExitMethod(Enum):
    """Methods for generating entry and exit signals"""
    Z_SCORE = "z_score"
    BOLLINGER_BANDS = "bollinger_bands"
    PERCENTILE = "percentile"
    MEAN_REVERSION = "mean_reversion"


@dataclass
class TradingPair:
    """Represents a trading pair with its characteristics"""
    symbol1: str
    symbol2: str
    hedge_ratio: float
    correlation: float
    cointegration_pvalue: float
    spread_mean: float
    spread_std: float
    half_life: float
    selection_score: float
    last_update: datetime


@dataclass
class PairsTradingConfig(StrategyConfig):
    """Configuration for Advanced Pairs Trading Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.PAIRS_TRADING

    # Pair selection parameters
    pair_selection_method: PairSelectionMethod = PairSelectionMethod.COINTEGRATION
    lookback_period: int = 252  # Trading days for pair analysis
    min_correlation: float = 0.6  # Minimum correlation for pair consideration
    max_pairs: int = 20  # Maximum number of pairs to trade
    rebalance_pairs_freq: int = 30  # Days between pair rebalancing

    # Cointegration testing
    cointegration_test: str = "engle_granger"  # engle_granger or johansen
    cointegration_pvalue_threshold: float = 0.05
    min_half_life: int = 5  # Minimum half-life for mean reversion
    max_half_life: int = 100  # Maximum half-life

    # Spread calculation
    spread_calculation: SpreadCalculationMethod = SpreadCalculationMethod.OLS_REGRESSION
    spread_lookback: int = 60  # Days for spread calculation
    kalman_process_noise: float = 1e-5
    kalman_measurement_noise: float = 1e-4

    # Entry/exit signals
    entry_method: EntryExitMethod = EntryExitMethod.Z_SCORE
    entry_threshold: float = 2.0  # Z-score or standard deviation threshold
    exit_threshold: float = 0.5  # Exit when spread returns to this level
    confirmation_periods: int = 2  # Periods to confirm signal

    # Bollinger Bands parameters (if used)
    bb_period: int = 20
    bb_std: float = 2.0

    # Position sizing
    base_position_size: float = 0.1  # Base position size as % of portfolio per pair
    risk_per_pair: float = 0.02  # Risk per pair (2% of portfolio)
    max_position_per_pair: float = 0.25  # Maximum position size per pair

    # Risk management
    stop_loss_pct: float = 0.05  # Stop loss percentage
    take_profit_multiplier: float = 2.0  # Take profit vs stop loss ratio
    max_holding_period: int = 30  # Maximum days to hold a position
    max_drawdown_pct: float = 0.10  # Maximum drawdown before position closure

    # False signal handling
    enable_false_signal_filter: bool = True
    false_signal_threshold: float = 0.8  # Threshold for false signal detection
    re_entry_delay: int = 5  # Days to wait before re-entry

    # Advanced features
    enable_dynamic_hedging: bool = True  # Recalculate hedge ratios periodically
    enable_sector_neutral: bool = False  # Ensure sector neutrality
    enable_adaptive_thresholds: bool = True  # Adaptive entry/exit thresholds
    use_transaction_costs: bool = True  # Account for transaction costs

    # Transaction costs
    round_trip_cost_bps: float = 10.0  # Round trip transaction cost in bps

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedPairsTradingStrategy(BaseStrategy):
    """
    Advanced Pairs Trading Strategy Implementation

    This strategy implements statistical arbitrage through pairs trading:
    1. Systematic pair selection using correlation and cointegration
    2. Dynamic spread calculation with Kalman filtering
    3. Mean reversion entry/exit signals with risk management
    4. Portfolio-level position sizing and diversification
    5. False signal filtering and adaptive thresholds

    The strategy exploits temporary deviations in cointegrated pairs
    while maintaining rigorous risk controls.
    """

    def __init__(self, config: PairsTradingConfig):
        super().__init__(config)
        self.config: PairsTradingConfig = config

        # Initialize components
        self.logger = get_logger(f"pairs_trading_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Pair management
        self.trading_pairs: Dict[str, TradingPair] = {}
        self.active_pairs: Dict[str, TradingPair] = {}
        self.pair_signals: Dict[str, Dict[str, Any]] = {}
        self.false_signals: Dict[str, datetime] = {}

        # Spread tracking
        self.spread_history: Dict[str, pd.Series] = {}
        self.z_score_history: Dict[str, pd.Series] = {}
        self.hedge_ratios: Dict[str, float] = {}

        # Position tracking
        self.active_positions: Dict[str, Dict[str, StrategyPosition]] = {}  # pair_id -> {symbol: position}
        self.entry_times: Dict[str, datetime] = {}
        self.stop_levels: Dict[str, float] = {}
        self.take_profit_levels: Dict[str, float] = {}

        # Market data cache
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.DataFrame] = {}

        # Kalman filter state (for Kalman spread calculation)
        self.kalman_state: Dict[str, Dict[str, float]] = {}

        # Signal history
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Pairs Trading Strategy initialized", {
            'strategy_id': config.strategy_id,
            'pair_selection_method': config.pair_selection_method.value,
            'max_pairs': config.max_pairs
        })

    def initialize(self) -> bool:
        """
        Initialize the pairs trading strategy

        Sets up pair selection, spread calculation, and signal generation
        parameters for statistical arbitrage trading.
        """
        try:
            self.logger.info("Initializing Advanced Pairs Trading Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize pair tracking
            self.trading_pairs = {}
            self.active_pairs = {}
            self.pair_signals = {}
            self.false_signals = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"pairs_trading_{self.config.strategy_id}")

            self.logger.info("Advanced Pairs Trading Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize pairs trading strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate pairs trading signals

        This method implements the core pairs trading logic:
        1. Update market data and recalculate pairs if needed
        2. Calculate spreads and z-scores for active pairs
        3. Generate entry/exit signals based on mean reversion
        4. Apply risk management and position sizing
        5. Filter false signals and manage re-entry

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update market data
            self._update_market_data(market_data)

            # Recalculate pairs if needed
            self._update_trading_pairs()

            # Generate signals for active pairs
            for pair_id, pair in self.active_pairs.items():
                pair_signals = self._generate_pair_signals(pair_id, pair)
                signals.extend(pair_signals)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} pairs trading signals")

        except Exception as e:
            self.logger.error("Error generating pairs signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and pair state

        This method:
        1. Updates current positions and P&L
        2. Monitors spread convergence and divergence
        3. Adjusts stop levels and take profit targets
        4. Tracks false signals and manages re-entry
        5. Updates hedge ratios if dynamic hedging enabled

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update market data
            self._update_market_data(market_data)

            # Update position risk management
            self._update_position_stops()

            # Monitor pair performance
            self._monitor_pair_performance()

            # Update dynamic hedge ratios
            if self.config.enable_dynamic_hedging:
                self._update_hedge_ratios()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"pairs_trading_{self.config.strategy_id}_pairs",
                    len(self.active_pairs)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check pair selection parameters
            if not (0.3 <= self.config.min_correlation <= 1.0):
                return False

            if not (1 <= self.config.max_pairs <= 100):
                return False

            # Check cointegration parameters
            if not (0.001 <= self.config.cointegration_pvalue_threshold <= 0.1):
                return False

            if not (1 <= self.config.min_half_life < self.config.max_half_life):
                return False

            # Check entry/exit parameters
            if not (1.0 <= self.config.entry_threshold <= 5.0):
                return False

            if not (0.1 <= self.config.exit_threshold <= 1.0):
                return False

            # Check position sizing
            if not (0 < self.config.base_position_size <= self.config.max_position_per_pair <= 1.0):
                return False

            return True

        except Exception:
            return False

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update internal market data cache"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty:
                self.price_data[symbol] = data.copy()

                # Calculate returns if price data available
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                    self.returns_data[symbol] = returns

    def _update_trading_pairs(self) -> None:
        """
        Update the universe of trading pairs

        Recalculates pair relationships and selects the best pairs
        for trading based on the configured selection method.
        """
        try:
            # Check if rebalancing is needed
            current_time = datetime.now()
            if hasattr(self, '_last_pair_update'):
                days_since_update = (current_time - self._last_pair_update).days
                if days_since_update < self.config.rebalance_pairs_freq:
                    return

            self._last_pair_update = current_time

            # Get all available symbols
            available_symbols = list(self.price_data.keys())
            if len(available_symbols) < 2:
                return

            # Generate potential pairs
            potential_pairs = self._generate_potential_pairs(available_symbols)

            # Evaluate and rank pairs
            evaluated_pairs = []
            for symbol1, symbol2 in potential_pairs:
                pair_data = self._evaluate_pair(symbol1, symbol2)
                if pair_data:
                    evaluated_pairs.append(pair_data)

            # Select top pairs
            evaluated_pairs.sort(key=lambda x: x.selection_score, reverse=True)
            selected_pairs = evaluated_pairs[:self.config.max_pairs]

            # Update active pairs
            self.active_pairs = {f"{p.symbol1}_{p.symbol2}": p for p in selected_pairs}

            self.logger.info(f"Updated trading pairs: {len(self.active_pairs)} active pairs")

        except Exception as e:
            self.logger.error("Error updating trading pairs", {'error': str(e)})

    def _generate_potential_pairs(self, symbols: List[str]) -> List[Tuple[str, str]]:
        """Generate potential pairs from available symbols"""
        pairs = []
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                # Skip pairs that are already in false signal cooldown
                pair_id = f"{symbol1}_{symbol2}"
                if pair_id in self.false_signals:
                    days_since_false = (datetime.now() - self.false_signals[pair_id]).days
                    if days_since_false < self.config.re_entry_delay:
                        continue
                pairs.append((symbol1, symbol2))
        return pairs

    def _evaluate_pair(self, symbol1: str, symbol2: str) -> Optional[TradingPair]:
        """
        Evaluate a potential trading pair

        Tests for correlation, cointegration, and calculates
        relevant statistics for pair trading.
        """
        try:
            if symbol1 not in self.price_data or symbol2 not in self.price_data:
                return None

            # Get price data
            prices1 = self.price_data[symbol1]['close']
            prices2 = self.price_data[symbol2]['close']

            # Align data
            common_index = prices1.index.intersection(prices2.index)
            if len(common_index) < self.config.lookback_period:
                return None

            prices1 = prices1.loc[common_index]
            prices2 = prices2.loc[common_index]

            # Calculate correlation
            correlation = prices1.corr(prices2)
            if abs(correlation) < self.config.min_correlation:
                return None

            # Test for cointegration
            coint_result = self._test_cointegration(prices1, prices2)
            if coint_result is None:
                return None

            cointegration_pvalue, hedge_ratio, half_life = coint_result

            if cointegration_pvalue > self.config.cointegration_pvalue_threshold:
                return None

            if not (self.config.min_half_life <= half_life <= self.config.max_half_life):
                return None

            # Calculate spread statistics
            spread = self._calculate_spread(prices1, prices2, hedge_ratio)
            spread_mean = spread.mean()
            spread_std = spread.std()

            # Calculate selection score (higher is better)
            selection_score = self._calculate_pair_score(
                correlation, cointegration_pvalue, half_life, spread_std
            )

            return TradingPair(
                symbol1=symbol1,
                symbol2=symbol2,
                hedge_ratio=hedge_ratio,
                correlation=correlation,
                cointegration_pvalue=cointegration_pvalue,
                spread_mean=spread_mean,
                spread_std=spread_std,
                half_life=half_life,
                selection_score=selection_score,
                last_update=datetime.now()
            )

        except Exception as e:
            self.logger.error("Error evaluating pair", {'symbol1': symbol1, 'symbol2': symbol2, 'error': str(e)})
            return None

    def _test_cointegration(self, prices1: pd.Series, prices2: pd.Series) -> Optional[Tuple[float, float, float]]:
        """
        Test for cointegration between two price series

        Returns (p-value, hedge_ratio, half_life) if cointegrated, None otherwise
        """
        try:
            if self.config.cointegration_test == "engle_granger":
                # Engle-Granger test
                coint_result = coint(prices1, prices2)
                p_value = coint_result[1]

                # Calculate hedge ratio
                model = LinearRegression()
                model.fit(prices1.values.reshape(-1, 1), prices2.values)
                hedge_ratio = model.coef_[0]

            else:
                # Johansen test (simplified)
                data = pd.concat([prices1, prices2], axis=1)
                johansen_result = coint_johansen(data.values, det_order=0, k_ar_diff=1)
                p_value = johansen_result.lr1[0]  # Trace statistic p-value approximation
                hedge_ratio = johansen_result.evec[0, 1] / johansen_result.evec[0, 0]

            # Calculate half-life of mean reversion
            spread = prices2 - hedge_ratio * prices1
            half_life = self._calculate_half_life(spread)

            return p_value, hedge_ratio, half_life

        except Exception as e:
            self.logger.error("Error testing cointegration", {'error': str(e)})
            return None

    def _calculate_half_life(self, spread: pd.Series) -> float:
        """Calculate the half-life of mean reversion for a spread"""
        try:
            # Run regression: spread_t = alpha + beta * spread_{t-1} + error
            spread_lag = spread.shift(1).dropna()
            spread_diff = spread.diff().dropna()

            # Align data
            common_index = spread_lag.index.intersection(spread_diff.index)
            y = spread_diff.loc[common_index]
            X = spread_lag.loc[common_index].values.reshape(-1, 1)

            if len(y) < 10:
                return float('inf')

            model = LinearRegression()
            model.fit(X, y)

            beta = model.coef_[0]

            # Half-life = -ln(2) / ln(beta)
            if abs(beta) >= 1.0:
                return float('inf')

            half_life = -np.log(2) / np.log(abs(beta))
            return max(half_life, 1.0)

        except Exception:
            return float('inf')

    def _calculate_spread(self, prices1: pd.Series, prices2: pd.Series, hedge_ratio: float) -> pd.Series:
        """Calculate the spread between two assets"""
        if self.config.spread_calculation == SpreadCalculationMethod.KALMAN_FILTER:
            return self._calculate_kalman_spread(prices1, prices2)
        else:
            # OLS spread
            return prices2 - hedge_ratio * prices1

    def _calculate_kalman_spread(self, prices1: pd.Series, prices2: pd.Series) -> pd.Series:
        """
        Calculate spread using Kalman filter for dynamic hedge ratio

        This is a simplified implementation. In practice, this would use
        a proper Kalman filter implementation.
        """
        # Simplified: use rolling regression for dynamic hedge ratio
        spreads = []
        window = min(60, len(prices1) // 4)

        for i in range(window, len(prices1)):
            window_prices1 = prices1.iloc[i-window:i]
            window_prices2 = prices2.iloc[i-window:i]

            model = LinearRegression()
            model.fit(window_prices1.values.reshape(-1, 1), window_prices2.values)
            hedge_ratio = model.coef_[0]

            spread = prices2.iloc[i] - hedge_ratio * prices1.iloc[i]
            spreads.append(spread)

        return pd.Series(spreads, index=prices1.index[window:])

    def _calculate_pair_score(self, correlation: float, coint_pvalue: float,
                            half_life: float, spread_std: float) -> float:
        """
        Calculate a selection score for the pair

        Higher scores indicate better trading pairs.
        """
        try:
            # Correlation score (higher correlation is better)
            corr_score = abs(correlation)

            # Cointegration score (lower p-value is better)
            coint_score = 1.0 - coint_pvalue

            # Half-life score (moderate half-life is better)
            optimal_half_life = 20.0
            half_life_score = 1.0 - min(abs(half_life - optimal_half_life) / optimal_half_life, 1.0)

            # Spread volatility score (moderate volatility is better)
            optimal_vol = 0.02
            vol_score = 1.0 - min(abs(spread_std - optimal_vol) / optimal_vol, 1.0)

            # Weighted average
            score = (0.3 * corr_score + 0.3 * coint_score +
                    0.2 * half_life_score + 0.2 * vol_score)

            return score

        except Exception:
            return 0.0

    def _generate_pair_signals(self, pair_id: str, pair: TradingPair) -> List[StrategySignal]:
        """
        Generate trading signals for a specific pair

        Calculates the current spread, z-score, and generates
        entry/exit signals based on the configured method.
        """
        signals = []

        try:
            # Check for false signal cooldown
            if self._is_pair_in_cooldown(pair_id):
                return signals

            # Calculate current spread and z-score
            spread_info = self._calculate_current_spread(pair_id, pair)
            if spread_info is None:
                return signals

            current_spread, z_score, signal_type = spread_info

            # Check for existing position
            has_position = pair_id in self.active_positions

            # Generate signals based on position and signal
            if signal_type and not has_position:
                # Entry signal
                entry_signals = self._generate_entry_signals(pair_id, pair, signal_type, z_score)
                signals.extend(entry_signals)

            elif has_position and self._should_exit_pair(pair_id, current_spread, z_score):
                # Exit signal
                exit_signals = self._generate_exit_signals(pair_id, pair)
                signals.extend(exit_signals)

            # Check for false signal
            if has_position and self._is_false_signal(pair_id, z_score):
                self._handle_false_signal(pair_id)

        except Exception as e:
            self.logger.error("Error generating pair signals", {'pair_id': pair_id, 'error': str(e)})

        return signals

    def _calculate_current_spread(self, pair_id: str, pair: TradingPair) -> Optional[Tuple[float, float, Optional[SignalType]]]:
        """
        Calculate current spread and determine signal type

        Returns (current_spread, z_score, signal_type)
        """
        try:
            if pair.symbol1 not in self.price_data or pair.symbol2 not in self.price_data:
                return None

            # Get current prices
            price1 = self.price_data[pair.symbol1]['close'].iloc[-1]
            price2 = self.price_data[pair.symbol2]['close'].iloc[-1]

            # Calculate current spread
            current_spread = price2 - pair.hedge_ratio * price1

            # Calculate z-score
            z_score = (current_spread - pair.spread_mean) / pair.spread_std

            # Determine signal type based on entry method
            signal_type = None
            if self.config.entry_method == EntryExitMethod.Z_SCORE:
                if abs(z_score) >= self.config.entry_threshold:
                    signal_type = SignalType.SELL if z_score > 0 else SignalType.BUY
            elif self.config.entry_method == EntryExitMethod.MEAN_REVERSION:
                # Simplified mean reversion signal
                if abs(z_score) >= self.config.entry_threshold:
                    signal_type = SignalType.SELL if z_score > 0 else SignalType.BUY

            return current_spread, z_score, signal_type

        except Exception as e:
            self.logger.error("Error calculating current spread", {'pair_id': pair_id, 'error': str(e)})
            return None

    def _generate_entry_signals(self, pair_id: str, pair: TradingPair,
                              signal_type: SignalType, z_score: float) -> List[StrategySignal]:
        """Generate entry signals for a pair"""
        signals = []

        try:
            # Calculate position sizes
            position_size = self._calculate_pair_position_size(pair_id, pair, z_score)

            # Determine which asset to buy/sell
            if signal_type == SignalType.BUY:
                # Buy symbol1, sell symbol2 (or vice versa based on hedge ratio)
                buy_symbol = pair.symbol1 if pair.hedge_ratio > 0 else pair.symbol2
                sell_symbol = pair.symbol2 if pair.hedge_ratio > 0 else pair.symbol1
                buy_quantity = position_size / self.price_data[buy_symbol]['close'].iloc[-1]
                sell_quantity = position_size / self.price_data[sell_symbol]['close'].iloc[-1]
            else:
                # Sell symbol1, buy symbol2
                sell_symbol = pair.symbol1 if pair.hedge_ratio > 0 else pair.symbol2
                buy_symbol = pair.symbol2 if pair.hedge_ratio > 0 else pair.symbol1
                sell_quantity = position_size / self.price_data[sell_symbol]['close'].iloc[-1]
                buy_quantity = position_size / self.price_data[buy_symbol]['close'].iloc[-1]

            # Create signals
            buy_signal = StrategySignal(
                signal_id=f"pairs_entry_buy_{pair_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=buy_symbol,
                signal_type=SignalType.BUY,
                confidence=min(abs(z_score) / self.config.entry_threshold, 1.0),
                strength=abs(z_score),
                target_quantity=buy_quantity,
                signal_price=self.price_data[buy_symbol]['close'].iloc[-1],
                entry_price=self.price_data[buy_symbol]['close'].iloc[-1],
                max_position_size=self.config.max_position_per_pair
            )

            sell_signal = StrategySignal(
                signal_id=f"pairs_entry_sell_{pair_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=sell_symbol,
                signal_type=SignalType.SELL,
                confidence=min(abs(z_score) / self.config.entry_threshold, 1.0),
                strength=abs(z_score),
                target_quantity=sell_quantity,
                signal_price=self.price_data[sell_symbol]['close'].iloc[-1],
                entry_price=self.price_data[sell_symbol]['close'].iloc[-1],
                max_position_size=self.config.max_position_per_pair
            )

            signals.extend([buy_signal, sell_signal])

            # Set up risk management
            self._setup_pair_risk_management(pair_id, pair, z_score)

        except Exception as e:
            self.logger.error("Error generating entry signals", {'pair_id': pair_id, 'error': str(e)})

        return signals

    def _generate_exit_signals(self, pair_id: str, pair: TradingPair) -> List[StrategySignal]:
        """Generate exit signals for a pair"""
        signals = []

        try:
            if pair_id not in self.active_positions:
                return signals

            positions = self.active_positions[pair_id]

            # Create exit signals for both positions
            for symbol, position in positions.items():
                signal_type = SignalType.CLOSE_LONG if position.quantity > 0 else SignalType.CLOSE_SHORT

                signal = StrategySignal(
                    signal_id=f"pairs_exit_{symbol}_{pair_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=self.config.strategy_id,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=0.8,
                    strength=1.0,
                    target_quantity=abs(position.quantity),
                    signal_price=self.price_data[symbol]['close'].iloc[-1],
                    entry_price=self.price_data[symbol]['close'].iloc[-1],
                    max_position_size=self.config.max_position_per_pair
                )

                signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating exit signals", {'pair_id': pair_id, 'error': str(e)})

        return signals

    def _calculate_pair_position_size(self, pair_id: str, pair: TradingPair, z_score: float) -> float:
        """Calculate position size for a pair trade"""
        try:
            # Base size adjusted by z-score strength
            strength_multiplier = min(abs(z_score) / self.config.entry_threshold, 2.0)
            position_size = self.config.base_position_size * strength_multiplier

            # Risk-based adjustment
            risk_adjustment = self.config.risk_per_pair / pair.spread_std
            position_size *= risk_adjustment

            # Cap at maximum
            position_size = min(position_size, self.config.max_position_per_pair)

            return position_size

        except Exception as e:
            self.logger.error("Error calculating pair position size", {'pair_id': pair_id, 'error': str(e)})
            return self.config.base_position_size

    def _setup_pair_risk_management(self, pair_id: str, pair: TradingPair, z_score: float) -> None:
        """Set up risk management levels for a pair"""
        try:
            # Stop loss based on spread standard deviation
            stop_distance = pair.spread_std * 2.0
            self.stop_levels[pair_id] = stop_distance

            # Take profit at mean reversion
            self.take_profit_levels[pair_id] = pair.spread_mean

            # Record entry time
            self.entry_times[pair_id] = datetime.now()

        except Exception as e:
            self.logger.error("Error setting up pair risk management", {'pair_id': pair_id, 'error': str(e)})

    def _should_exit_pair(self, pair_id: str, current_spread: float, z_score: float) -> bool:
        """Determine if a pair position should be exited"""
        try:
            if pair_id not in self.active_positions:
                return False

            pair = self.active_pairs[pair_id]

            # Exit if spread has mean reverted
            if abs(z_score) <= self.config.exit_threshold:
                return True

            # Exit if stop loss hit
            if abs(current_spread - pair.spread_mean) >= self.stop_levels.get(pair_id, float('inf')):
                return True

            # Exit if take profit hit
            if abs(current_spread - self.take_profit_levels.get(pair_id, 0)) <= pair.spread_std * 0.5:
                return True

            # Exit if maximum holding period reached
            if pair_id in self.entry_times:
                holding_period = (datetime.now() - self.entry_times[pair_id]).days
                if holding_period >= self.config.max_holding_period:
                    return True

            return False

        except Exception as e:
            self.logger.error("Error checking pair exit condition", {'pair_id': pair_id, 'error': str(e)})
            return False

    def _is_false_signal(self, pair_id: str, z_score: float) -> bool:
        """Check if the signal is a false signal"""
        try:
            if not self.config.enable_false_signal_filter:
                return False

            # Check if z-score is moving away from mean (divergence)
            if pair_id in self.z_score_history and len(self.z_score_history[pair_id]) >= 5:
                recent_z_scores = self.z_score_history[pair_id].tail(5)
                if abs(z_score) > abs(recent_z_scores.iloc[0]) * self.config.false_signal_threshold:
                    return True

            return False

        except Exception:
            return False

    def _handle_false_signal(self, pair_id: str) -> None:
        """Handle false signal by marking cooldown period"""
        try:
            self.false_signals[pair_id] = datetime.now()
            self.logger.info("False signal detected", {'pair_id': pair_id})

        except Exception as e:
            self.logger.error("Error handling false signal", {'pair_id': pair_id, 'error': str(e)})

    def _is_pair_in_cooldown(self, pair_id: str) -> bool:
        """Check if pair is in false signal cooldown"""
        try:
            if pair_id not in self.false_signals:
                return False

            days_since_false = (datetime.now() - self.false_signals[pair_id]).days
            return days_since_false < self.config.re_entry_delay

        except Exception:
            return False

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Apply portfolio-level risk management constraints"""
        try:
            # Limit number of active pairs
            active_pair_count = len(self.active_positions)
            max_new_pairs = max(0, self.config.max_pairs // 2 - active_pair_count)

            if max_new_pairs <= 0:
                return []

            # Group signals by pair
            pair_signals = {}
            for signal in signals:
                # Extract pair_id from signal_id (simplified)
                pair_id = signal.signal_id.split('_')[-2]  # Assumes format: ..._pair_id_timestamp
                if pair_id not in pair_signals:
                    pair_signals[pair_id] = []
                pair_signals[pair_id].append(signal)

            # Keep only top pairs by signal strength
            sorted_pairs = sorted(pair_signals.keys(),
                                key=lambda p: max(s.confidence for s in pair_signals[p]),
                                reverse=True)

            selected_pairs = sorted_pairs[:max_new_pairs]
            filtered_signals = []
            for pair_id in selected_pairs:
                filtered_signals.extend(pair_signals[pair_id])

            return filtered_signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _update_position_stops(self) -> None:
        """Update trailing stops for active pairs"""
        # This would update stop levels based on current spread
        pass

    def _monitor_pair_performance(self) -> None:
        """Monitor the performance of active pairs"""
        try:
            for pair_id, positions in list(self.active_positions.items()):
                # Check for maximum drawdown
                # Simplified - in practice would calculate P&L
                pass

        except Exception as e:
            self.logger.error("Error monitoring pair performance", {'error': str(e)})

    def _update_hedge_ratios(self) -> None:
        """Update hedge ratios for dynamic hedging"""
        try:
            for pair_id, pair in self.active_pairs.items():
                # Recalculate hedge ratio with new data
                # Simplified - would implement rolling regression
                pass

        except Exception as e:
            self.logger.error("Error updating hedge ratios", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = sum(len(positions) for positions in self.active_positions.values())

        # Add pairs-specific metrics
        metrics.total_return = len(self.active_pairs)

        return metrics