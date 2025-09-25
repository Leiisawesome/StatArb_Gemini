"""
Advanced Mean Reversion Strategy Implementation

This module implements a sophisticated mean reversion trading strategy that combines
statistical analysis with rigorous risk management and academic methodologies.

The strategy uses:
- Augmented Dickey-Fuller (ADF) tests for stationarity
- Hurst exponent analysis for mean reversion strength
- Z-score based entry/exit signals
- Half-life estimation for optimal holding periods
- Volatility-adjusted position sizing

Key Features:
- Statistical significance testing
- Multiple mean reversion indicators
- Adaptive lookback periods
- Risk parity position sizing
- Transaction cost awareness

Academic Foundations:
- Engle & Granger (1987) cointegration
- Phillips & Perron (1988) unit root tests
- Hurst (1951) rescaled range analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.ar_model import AutoReg
from sklearn.preprocessing import StandardScaler

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class MeanReversionType(Enum):
    """Types of mean reversion indicators"""
    PRICE_BASED = "price_based"  # Simple moving average reversion
    STATISTICAL = "statistical"  # Z-score based reversion
    COINTEGRATION = "cointegration"  # Engle-Granger cointegration
    ARBITRAGE = "arbitrage"  # Statistical arbitrage spreads


@dataclass
class MeanReversionConfig(StrategyConfig):
    """Configuration for Advanced Mean Reversion Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.MEAN_REVERSION

    # Core mean reversion parameters
    lookback_periods: List[int] = field(default_factory=lambda: [20, 50, 100, 200])  # Days
    entry_threshold: float = 2.0  # Z-score entry threshold
    exit_threshold: float = 0.5  # Z-score exit threshold

    # Statistical testing parameters
    adf_confidence_level: float = 0.05  # ADF test significance level
    min_half_life: int = 5  # Minimum half-life for mean reversion
    max_half_life: int = 100  # Maximum half-life for mean reversion

    # Mean reversion types to use
    reversion_types: List[MeanReversionType] = field(default_factory=lambda: [
        MeanReversionType.PRICE_BASED,
        MeanReversionType.STATISTICAL
    ])

    # Signal generation thresholds
    min_reversion_strength: float = 0.6  # Minimum mean reversion strength (0-1)
    max_z_score: float = 4.0  # Maximum z-score to avoid outliers

    # Risk management
    max_position_size: float = 0.15  # Max position as % of portfolio
    volatility_target: float = 0.12  # Annualized volatility target
    max_holding_period: int = 20  # Maximum holding period in days

    # Transaction costs and slippage
    transaction_cost_bps: float = 5.0  # Basis points per trade
    slippage_bps: float = 3.0  # Expected slippage in basis points

    # Rebalancing and timing
    rebalance_frequency: str = "daily"  # daily, weekly
    entry_timing: str = "close"  # close, open, vwap

    # Advanced features
    use_adaptive_lookback: bool = True
    use_risk_parity: bool = True
    use_half_life_sizing: bool = True
    enable_stop_loss: bool = True
    enable_take_profit: bool = True

    # Stop loss and take profit
    stop_loss_pct: float = 0.08
    take_profit_pct: float = 0.12
    trailing_stop_pct: float = 0.05

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedMeanReversionStrategy(BaseStrategy):
    """
    Advanced Mean Reversion Strategy Implementation

    This strategy implements multiple mean reversion approaches with academic rigor:
    1. Statistical mean reversion using z-scores and ADF tests
    2. Price-based mean reversion using moving averages
    3. Half-life estimation for optimal holding periods
    4. Risk-managed position sizing

    The strategy combines these approaches into a composite mean reversion score
    and generates signals based on statistical significance and market conditions.
    """

    def __init__(self, config: MeanReversionConfig):
        super().__init__(config)
        self.config: MeanReversionConfig = config

        # Initialize components
        self.logger = get_logger(f"mean_reversion_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Strategy state
        self.mean_levels: Dict[str, pd.Series] = {}
        self.std_levels: Dict[str, pd.Series] = {}
        self.z_scores: Dict[str, pd.Series] = {}
        self.half_lives: Dict[str, float] = {}
        self.position_entry_times: Dict[str, datetime] = {}
        self.position_sizes: Dict[str, float] = {}

        # Market data cache for efficiency
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.DataFrame] = {}

        # Risk management state
        self.portfolio_volatility: float = 0.0

        # Signal history for analysis
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Mean Reversion Strategy initialized", {
            'strategy_id': config.strategy_id,
            'lookback_periods': config.lookback_periods,
            'entry_threshold': config.entry_threshold,
            'reversion_types': [rt.value for rt in config.reversion_types]
        })

    def initialize(self) -> bool:
        """
        Initialize the mean reversion strategy

        Sets up data structures, validates configuration, and prepares
        for signal generation with statistical testing.
        """
        # DEBUG: Log initialization
        if hasattr(self, 'logger'):
            self.logger.info("DEBUG: Mean reversion strategy initialize() called")
        try:
            self.logger.info("Initializing Advanced Mean Reversion Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize data structures
            self.mean_levels = {}
            self.std_levels = {}
            self.z_scores = {}
            self.half_lives = {}
            self.position_entry_times = {}
            self.position_sizes = {}
            self.signal_history = []

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"mean_reversion_{self.config.strategy_id}")

            # Initialize risk management
            self.portfolio_volatility = self.config.volatility_target

            self.logger.info("Advanced Mean Reversion Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize mean reversion strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate mean reversion-based trading signals

        This method implements the core mean reversion logic:
        1. Calculate mean reversion statistics for all assets
        2. Test for stationarity and mean reversion strength
        3. Generate entry/exit signals based on z-score thresholds
        4. Apply risk management constraints

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        # Generate signals based on market data
        signals = []

        try:
            if not market_data:
                return signals
            
            # Update internal data cache
            self._update_market_data(market_data)

            # Calculate mean reversion statistics for all symbols
            reversion_stats = self._calculate_mean_reversion_stats()

            # Generate signals based on statistical analysis
            for symbol, stats in reversion_stats.items():
                signal = self._generate_signal_for_symbol(symbol, stats, market_data.get(symbol))
                if signal:
                    signals.append(signal)
                    self.signal_history.append(signal)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} mean reversion signals")

        except Exception as e:
            self.logger.error("Error generating mean reversion signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def _test_stationarity(self, series: pd.Series, symbol: str = "") -> Dict[str, Any]:
        """
        Test stationarity using ADF and KPSS tests
        
        Academic Foundation:
        - Augmented Dickey-Fuller (ADF) test: Dickey & Fuller (1979, 1981)
        - KPSS test: Kwiatkowski et al. (1992)
        - Combined approach for robust stationarity assessment
        
        Args:
            series: Time series to test for stationarity
            symbol: Symbol name for logging
            
        Returns:
            Dictionary containing stationarity test results
        """
        try:
            from statsmodels.tsa.stattools import adfuller, kpss
            
            if len(series) < 10:
                return {
                    'adf_stationary': False,
                    'kpss_stationary': False,
                    'consensus_stationary': False,
                    'error': 'Insufficient data points'
                }
            
            # Remove NaN values
            clean_series = series.dropna()
            if len(clean_series) < 10:
                return {
                    'adf_stationary': False,
                    'kpss_stationary': False,
                    'consensus_stationary': False,
                    'error': 'Insufficient clean data points'
                }
            
            # ADF Test (H0: unit root exists, i.e., non-stationary)
            adf_stat, adf_p_value, adf_used_lag, adf_nobs, adf_critical_values, adf_icbest = adfuller(
                clean_series, autolag='AIC', regression='c'
            )
            
            # KPSS Test (H0: stationary)
            kpss_stat, kpss_p_value, kpss_lags, kpss_critical_values = kpss(
                clean_series, regression='c', nlags='auto'
            )
            
            # Interpret results
            adf_stationary = adf_p_value < self.config.adf_confidence_level
            kpss_stationary = kpss_p_value > self.config.adf_confidence_level
            
            # Consensus: both tests must agree
            consensus_stationary = adf_stationary and kpss_stationary
            
            # Log results for debugging
            if symbol:
                self.logger.debug(f"Stationarity test for {symbol}: ADF p={adf_p_value:.4f}, KPSS p={kpss_p_value:.4f}, Consensus={consensus_stationary}")
            
            return {
                'adf_statistic': float(adf_stat),
                'adf_p_value': float(adf_p_value),
                'adf_critical_values': {k: float(v) for k, v in adf_critical_values.items()},
                'adf_stationary': adf_stationary,
                'kpss_statistic': float(kpss_stat),
                'kpss_p_value': float(kpss_p_value),
                'kpss_critical_values': {k: float(v) for k, v in kpss_critical_values.items()},
                'kpss_stationary': kpss_stationary,
                'consensus_stationary': consensus_stationary,
                'data_points': len(clean_series),
                'test_confidence_level': self.config.adf_confidence_level
            }
            
        except Exception as e:
            self.logger.error(f"Stationarity test failed for {symbol}: {e}")
            return {
                'adf_stationary': False,
                'kpss_stationary': False,
                'consensus_stationary': False,
                'error': str(e)
            }

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and risk management

        This method:
        1. Updates current positions based on market data
        2. Checks holding periods and exit conditions
        3. Updates mean reversion statistics
        4. Monitors portfolio risk metrics

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update position valuations
            self._update_position_valuations(market_data)

            # Check holding periods and exit conditions
            exit_signals = self._check_holding_periods_and_exits(market_data)

            # Update mean reversion statistics
            self._update_mean_reversion_statistics(market_data)

            # Update portfolio risk metrics
            self._update_portfolio_risk_metrics()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"mean_reversion_{self.config.strategy_id}_positions",
                    len(self.position_sizes)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check lookback periods
            if not self.config.lookback_periods or min(self.config.lookback_periods) < 10:
                return False

            # Check thresholds - FIXED: entry_threshold should be > exit_threshold for mean reversion
            # Entry when far from mean (high z-score), exit when close to mean (low z-score)
            if not (0 < self.config.exit_threshold < self.config.entry_threshold):
                return False

            # Check statistical parameters
            if not (0 < self.config.adf_confidence_level < 1.0):
                return False

            if not (0 < self.config.min_half_life < self.config.max_half_life):
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
                    self.returns_data[symbol] = data['close'].pct_change().dropna()

    def _calculate_mean_reversion_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate comprehensive mean reversion statistics for all symbols

        Returns statistical measures including:
        - Z-scores from moving averages
        - ADF test results for stationarity
        - Half-life estimates
        - Mean reversion strength metrics
        """
        reversion_stats = {}
        
        # Calculate statistics for available symbols

        for symbol in self.price_data.keys():
            try:
                # Check minimum data requirement for statistical significance
                data_length = len(self.price_data[symbol])
                min_required = max(self.config.lookback_periods) + 10  # Need enough for longest lookback + buffer
                
                if data_length < min_required:
                    continue
                
                stats = self._calculate_symbol_reversion_stats(symbol)
                if stats and self._passes_statistical_tests(stats):
                    reversion_stats[symbol] = stats

            except Exception as e:
                self.logger.warning(f"Error calculating reversion stats for {symbol}", {'error': str(e)})
                continue

        return reversion_stats

    def _calculate_symbol_reversion_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Calculate mean reversion statistics for a single symbol

        Returns comprehensive statistics including z-scores, half-life,
        and statistical test results.
        """
        if symbol not in self.price_data or 'close' not in self.price_data[symbol].columns:
            print(f"🔍 DEBUG: {symbol} missing price data or close column")
            return None

        prices = self.price_data[symbol]['close']

        if len(prices) < max(self.config.lookback_periods) + 10:
            return None

        stats = {}

        # Calculate z-scores for different lookback periods
        z_scores = {}
        for period in self.config.lookback_periods:
            if len(prices) >= period:
                mean = prices.rolling(period).mean()
                std = prices.rolling(period).std()
                z_score = (prices - mean) / std
                z_scores[period] = z_score.iloc[-1] if not z_score.empty else 0.0

        stats['z_scores'] = z_scores
        stats['primary_z_score'] = z_scores.get(max(self.config.lookback_periods), 0.0)
        
        # DEBUG: Log z-score values to understand why no signals are generated
        if hasattr(self, 'logger'):
            self.logger.info(f"DEBUG Z-SCORES for {symbol}: {z_scores}, primary: {stats['primary_z_score']}")

        # Calculate half-life of mean reversion
        half_life = self._calculate_half_life(prices)
        stats['half_life'] = half_life

        # Perform ADF test for stationarity
        adf_result = self._perform_adf_test(prices)
        stats['adf_statistic'] = adf_result[0]
        stats['adf_p_value'] = adf_result[1]
        stats['is_stationary'] = adf_result[1] < self.config.adf_confidence_level

        # Calculate mean reversion strength
        reversion_strength = self._calculate_reversion_strength(prices)
        stats['reversion_strength'] = reversion_strength

        # Store for future reference
        self.z_scores[symbol] = pd.Series(z_scores)
        self.half_lives[symbol] = half_life

        return stats

    def _calculate_half_life(self, prices: pd.Series) -> float:
        """
        Calculate the half-life of mean reversion (Phillips & Perron, 1988)

        The half-life measures how quickly a time series reverts to its mean.
        Shorter half-lives indicate stronger mean reversion.
        """
        try:
            # Calculate percentage deviation from moving average
            ma = prices.rolling(20).mean()
            deviation = (prices - ma) / ma

            # Remove NaN values
            deviation = deviation.dropna()

            if len(deviation) < 20:
                return float('inf')

            # Fit AR(1) model: deviation_t = phi * deviation_{t-1} + epsilon_t
            model = AutoReg(deviation, lags=1, old_names=False)
            results = model.fit()

            phi = results.params.iloc[1] if len(results.params) > 1 else 1.0

            # Half-life = -ln(2) / ln(phi) for |phi| < 1
            if abs(phi) >= 1.0:
                return float('inf')  # No mean reversion

            half_life = -np.log(2) / np.log(abs(phi))

            return max(1.0, min(half_life, 500.0))  # Reasonable bounds

        except Exception as e:
            self.logger.warning("Error calculating half-life", {'error': str(e)})
            return float('inf')

    def _perform_adf_test(self, prices: pd.Series) -> Tuple[float, float]:
        """
        Perform Augmented Dickey-Fuller test for stationarity

        Returns:
            Tuple of (ADF statistic, p-value)
        """
        try:
            # Use the longest available lookback period
            test_data = prices.tail(min(len(prices), max(self.config.lookback_periods)))

            if len(test_data) < 20:
                return (0.0, 1.0)  # Not enough data

            result = adfuller(test_data, autolag='AIC')
            return (result[0], result[1])  # ADF statistic and p-value

        except Exception as e:
            self.logger.warning("Error performing ADF test", {'error': str(e)})
            return (0.0, 1.0)

    def _calculate_reversion_strength(self, prices: pd.Series) -> float:
        """
        Calculate mean reversion strength using Hurst exponent approximation

        Returns value between 0 and 1, where higher values indicate
        stronger mean reversion (Hurst exponent closer to 0).
        """
        try:
            # Simplified Hurst exponent calculation
            returns = prices.pct_change().dropna()

            if len(returns) < 50:
                return 0.0

            # Calculate rescaled range for different time lags
            lags = [2, 4, 8, 16, 32]
            rs_values = []

            for lag in lags:
                if len(returns) >= lag:
                    # Calculate cumulative returns
                    cum_returns = returns.cumsum()

                    # Calculate range and standard deviation for each sub-period
                    ranges = []
                    for i in range(0, len(cum_returns) - lag + 1, lag):
                        segment = cum_returns.iloc[i:i+lag]
                        if len(segment) == lag:
                            range_val = segment.max() - segment.min()
                            std_val = segment.std()
                            if std_val > 0:
                                ranges.append(range_val / std_val)

                    if ranges:
                        rs_values.append(np.mean(ranges))

            if len(rs_values) < 2:
                return 0.0

            # Estimate Hurst exponent from log-log regression
            log_lags = np.log(lags[:len(rs_values)])
            log_rs = np.log(rs_values)

            slope, _, _, _, _ = stats.linregress(log_lags, log_rs)
            hurst_exponent = slope

            # Convert to reversion strength (H=0.5 is random walk, H<0.5 is mean reverting)
            if hurst_exponent <= 0.5:
                reversion_strength = 1.0 - (hurst_exponent / 0.5)
            else:
                reversion_strength = 0.0

            return max(0.0, min(1.0, reversion_strength))

        except Exception as e:
            self.logger.warning("Error calculating reversion strength", {'error': str(e)})
            return 0.0

    def _passes_statistical_tests(self, stats: Dict[str, Any]) -> bool:
        """
        Apply statistical filters to ensure mean reversion opportunity

        Checks:
        1. Stationarity (ADF test)
        2. Reasonable half-life
        3. Sufficient reversion strength
        4. Z-score within bounds
        """
        try:
            # Check stationarity
            if not stats.get('is_stationary', False):
                return False

            # Check half-life bounds
            half_life = stats.get('half_life', float('inf'))
            if not (self.config.min_half_life <= half_life <= self.config.max_half_life):
                return False

            # Check reversion strength
            if stats.get('reversion_strength', 0.0) < self.config.min_reversion_strength:
                return False

            # Check z-score bounds
            z_score = abs(stats.get('primary_z_score', 0.0))
            if z_score > self.config.max_z_score:
                return False

            return True

        except Exception as e:
            self.logger.error("Error in statistical tests", {'error': str(e)})
            return False

    def _generate_signal_for_symbol(self, symbol: str, stats: Dict[str, Any],
                                  market_data: Optional[pd.DataFrame]) -> Optional[StrategySignal]:
        """
        Generate a trading signal for a symbol based on mean reversion statistics

        Determines signal type based on z-score magnitude and direction,
        with consideration for existing positions and holding periods.
        """
        if market_data is None or market_data.empty:
            return None

        try:
            current_price = market_data['close'].iloc[-1]
            z_score = stats['primary_z_score']

            # Check existing position
            current_position = self.position_sizes.get(symbol, 0)
            entry_time = self.position_entry_times.get(symbol)

            # Check holding period limit
            if entry_time and (datetime.now() - entry_time).days > self.config.max_holding_period:
                # Force exit if holding too long
                if current_position != 0:
                    signal_type = SignalType.SELL if current_position > 0 else SignalType.BUY
                    return self._create_exit_signal(symbol, signal_type, current_price, "holding_period_limit")

            # Determine signal type based on z-score and position
            signal_type = self._determine_signal_type(z_score, current_position)

            if not signal_type:
                return None

            # Calculate position size
            position_size = self._calculate_position_size(symbol, stats, market_data)

            # Calculate risk management levels
            stop_loss, take_profit = self._calculate_risk_levels(
                signal_type, current_price, stats
            )

            # Create signal
            signal = StrategySignal(
                signal_id=f"mean_reversion_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                confidence=min(abs(z_score) / self.config.entry_threshold, 1.0),
                strength=abs(z_score),
                target_quantity=position_size,
                signal_price=current_price,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_position_size=self.config.max_position_size
            )

            return signal

        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}", {'error': str(e)})
            return None

    def _determine_signal_type(self, z_score: float, current_position: float) -> Optional[SignalType]:
        """
        Determine signal type based on z-score and current position

        Logic:
        - Enter long when z-score is significantly negative (price below mean)
        - Enter short when z-score is significantly positive (price above mean)
        - Exit when z-score approaches zero (price near mean)
        """
        abs_z_score = abs(z_score)

        # Exit conditions (close to mean)
        if abs_z_score <= self.config.exit_threshold:
            if current_position > 0:
                return SignalType.SELL  # Close long position
            elif current_position < 0:
                return SignalType.BUY   # Close short position

        # Entry conditions (far from mean)
        elif abs_z_score >= self.config.entry_threshold:
            if z_score < 0 and current_position <= 0:
                return SignalType.BUY   # Enter long
            elif z_score > 0 and current_position >= 0:
                return SignalType.SELL  # Enter short

        return None

    def _calculate_position_size(self, symbol: str, stats: Dict[str, Any],
                               market_data: pd.DataFrame) -> float:
        """
        Calculate position size using half-life and risk parity principles

        Incorporates:
        - Half-life based sizing (shorter half-life = larger position)
        - Reversion strength weighting
        - Volatility targeting
        - Maximum position limits
        """
        try:
            # Base position size from z-score magnitude
            z_score = abs(stats['primary_z_score'])
            base_size = min(z_score / self.config.entry_threshold, 1.0) * self.config.max_position_size

            # Adjust for half-life (shorter half-life = larger position)
            if self.config.use_half_life_sizing:
                half_life = stats.get('half_life', float('inf'))
                if half_life != float('inf'):
                    half_life_factor = 1.0 / (1.0 + half_life / 20.0)  # Shorter half-life increases size
                    base_size *= half_life_factor

            # Adjust for reversion strength
            reversion_strength = stats.get('reversion_strength', 0.0)
            base_size *= reversion_strength

            # Apply risk parity across positions if enabled
            if self.config.use_risk_parity and self.position_sizes:
                total_positions = len(self.position_sizes) + 1  # Include new position
                risk_parity_size = self.config.max_position_size / total_positions
                base_size = min(base_size, risk_parity_size)

            # Ensure within limits
            position_size = max(0.001, min(base_size, self.config.max_position_size))

            return position_size

        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}", {'error': str(e)})
            return self.config.max_position_size * 0.1  # Conservative fallback

    def _calculate_risk_levels(self, signal_type: SignalType, current_price: float,
                             stats: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop-loss and take-profit levels

        Uses statistical measures and configuration parameters
        to set appropriate risk levels.
        """
        try:
            if not self.config.enable_stop_loss and not self.config.enable_take_profit:
                return None, None

            # Base levels from configuration
            stop_loss_pct = self.config.stop_loss_pct
            take_profit_pct = self.config.take_profit_pct

            # Adjust based on half-life (longer half-life = wider stops)
            half_life = stats.get('half_life', 20.0)
            half_life_factor = min(half_life / 20.0, 2.0)  # Scale factor
            stop_loss_pct *= half_life_factor
            take_profit_pct *= half_life_factor

            # Calculate absolute levels
            if signal_type == SignalType.BUY:
                stop_loss = current_price * (1 - stop_loss_pct)
                take_profit = current_price * (1 + take_profit_pct)
            else:  # SELL
                stop_loss = current_price * (1 + stop_loss_pct)
                take_profit = current_price * (1 - take_profit_pct)

            return stop_loss, take_profit

        except Exception as e:
            self.logger.error("Error calculating risk levels", {'error': str(e)})
            return None, None

    def _create_exit_signal(self, symbol: str, signal_type: SignalType,
                           current_price: float, reason: str) -> StrategySignal:
        """Create an exit signal for risk management purposes"""
        return StrategySignal(
            signal_id=f"exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=self.config.strategy_id,
            timestamp=datetime.now(),
            symbol=symbol,
            signal_type=signal_type,
            confidence=1.0,  # Forced exit
            strength=1.0,
            target_quantity=0.0,  # Close position
            signal_price=current_price,
            entry_price=current_price,
            stop_loss=None,
            take_profit=None,
            max_position_size=self.config.max_position_size
        )

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """
        Apply portfolio-level risk management constraints

        Ensures the portfolio doesn't exceed volatility targets
        and maintains proper diversification.
        """
        if not signals:
            return signals

        try:
            # Check portfolio volatility
            if self.portfolio_volatility > self.config.volatility_target * 1.3:
                self.logger.warning("Portfolio volatility too high, reducing mean reversion exposure")
                # Reduce all position sizes
                for signal in signals:
                    signal.target_quantity *= 0.6

            return signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _update_position_valuations(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update position valuations with current market prices"""
        for symbol in list(self.position_sizes.keys()):
            if symbol in market_data and not market_data[symbol].empty:
                current_price = market_data[symbol]['close'].iloc[-1]
                # Update position tracking logic would go here

    def _check_holding_periods_and_exits(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Check holding periods and generate exit signals if needed"""
        exit_signals = []

        # Implementation for checking holding periods would go here
        # This would generate exit signals when positions exceed max holding period

        return exit_signals

    def _update_mean_reversion_statistics(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update mean reversion statistics for all symbols"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty and 'close' in data.columns:
                # Recalculate statistics periodically
                stats = self._calculate_symbol_reversion_stats(symbol)
                if stats:
                    # Update stored statistics
                    pass

    def _update_portfolio_risk_metrics(self) -> None:
        """Update portfolio-level risk metrics"""
        try:
            # Simplified portfolio volatility calculation
            if self.position_sizes:
                # This would calculate portfolio-level volatility based on positions
                pass

        except Exception as e:
            self.logger.error("Error updating portfolio risk metrics", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.position_sizes)

        # Add more detailed metrics as needed

        return metrics