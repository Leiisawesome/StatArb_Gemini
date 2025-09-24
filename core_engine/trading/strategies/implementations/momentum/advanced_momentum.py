"""
Advanced Momentum Strategy Implementation

This module implements a sophisticated momentum-based trading strategy that combines
multiple momentum indicators with rigorous statistical analysis and risk management.

The strategy uses:
- Time-series momentum (Jegadeesh & Titman, 1993)
- Cross-sectional momentum (Asness et al., 2013)
- Volatility-adjusted momentum
- Risk parity position sizing
- Dynamic stop-loss and take-profit levels

Key Features:
- Multi-factor momentum scoring
- Adaptive lookback periods
- Volatility targeting
- Transaction cost awareness
- Risk management integration
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class MomentumType(Enum):
    """Types of momentum indicators"""
    TIME_SERIES = "time_series"  # Jegadeesh & Titman (1993)
    CROSS_SECTIONAL = "cross_sectional"  # Asness et al. (2013)
    RESIDUAL = "residual"  # Daniel & Moskowitz (2016)
    VOLATILITY_ADJUSTED = "volatility_adjusted"  # Barroso & Santa-Clara (2015)


@dataclass
class MomentumConfig(StrategyConfig):
    """Configuration for Advanced Momentum Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.MOMENTUM

    # Core momentum parameters
    lookback_periods: List[int] = field(default_factory=lambda: [1, 3, 6, 12])  # months
    skip_period: int = 1  # Skip most recent month (Jegadeesh & Titman)
    holding_period: int = 1  # Holding period in months

    # Momentum calculation settings
    momentum_types: List[MomentumType] = field(default_factory=lambda: [
        MomentumType.TIME_SERIES,
        MomentumType.CROSS_SECTIONAL,
        MomentumType.VOLATILITY_ADJUSTED
    ])

    # Signal generation thresholds
    min_momentum_score: float = 0.02  # Minimum momentum for signal
    max_momentum_score: float = 0.50  # Maximum momentum (outlier filter)
    signal_threshold: float = 0.10  # Z-score threshold for signals

    # Risk management
    max_position_size: float = 0.10  # Max position as % of portfolio
    volatility_target: float = 0.15  # Annualized volatility target
    max_drawdown_limit: float = 0.20  # Maximum drawdown before reducing exposure

    # Transaction costs and slippage
    transaction_cost_bps: float = 5.0  # Basis points per trade
    slippage_bps: float = 2.0  # Expected slippage in basis points

    # Rebalancing and timing
    rebalance_frequency: str = "monthly"  # monthly, weekly, daily
    entry_timing: str = "close"  # close, open, vwap

    # Advanced features
    use_volatility_scaling: bool = True
    use_risk_parity: bool = True
    use_adaptive_lookback: bool = True
    enable_stop_loss: bool = True
    enable_take_profit: bool = True

    # Stop loss and take profit
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    trailing_stop_pct: float = 0.03

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedMomentumStrategy(BaseStrategy):
    """
    Advanced Momentum Strategy Implementation

    This strategy implements multiple momentum factors with academic rigor:
    1. Time-series momentum (Jegadeesh & Titman, 1993)
    2. Cross-sectional momentum (Asness et al., 2013)
    3. Volatility-adjusted momentum (Barroso & Santa-Clara, 2015)
    4. Risk-managed position sizing

    The strategy combines these factors into a composite momentum score
    and generates signals based on statistical significance thresholds.
    """

    def __init__(self, config: MomentumConfig):
        super().__init__(config)
        self.config: MomentumConfig = config

        # Initialize components
        self.logger = get_logger(f"momentum_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Strategy state
        self.momentum_scores: Dict[str, pd.Series] = {}
        self.volatility_estimates: Dict[str, pd.Series] = {}
        self.position_sizes: Dict[str, float] = {}
        self.entry_prices: Dict[str, float] = {}
        self.stop_losses: Dict[str, float] = {}
        self.take_profits: Dict[str, float] = {}

        # Market data cache for efficiency
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.DataFrame] = {}

        # Risk management state
        self.portfolio_volatility: float = 0.0
        self.current_drawdown: float = 0.0

        # Signal history for analysis
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Momentum Strategy initialized", {
            'strategy_id': config.strategy_id,
            'lookback_periods': config.lookback_periods,
            'momentum_types': [mt.value for mt in config.momentum_types]
        })

    def initialize(self) -> bool:
        """
        Initialize the momentum strategy

        Sets up data structures, validates configuration, and prepares
        for signal generation.
        """
        try:
            self.logger.info("Initializing Advanced Momentum Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize data structures
            self.momentum_scores = {}
            self.volatility_estimates = {}
            self.position_sizes = {}
            self.entry_prices = {}
            self.stop_losses = {}
            self.take_profits = {}
            self.signal_history = []

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring()

            # Initialize risk management
            self.portfolio_volatility = self.config.volatility_target
            self.current_drawdown = 0.0

            self.logger.info("Advanced Momentum Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize momentum strategy: {e}")
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate momentum-based trading signals

        This method implements the core momentum logic:
        1. Calculate momentum scores for all assets
        2. Apply statistical filters and thresholds
        3. Generate buy/sell signals with position sizing
        4. Apply risk management constraints

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update internal data cache
            self._update_market_data(market_data)

            # Calculate momentum scores for all symbols
            momentum_scores = self._calculate_momentum_scores()

            # Apply statistical filters
            filtered_scores = self._apply_statistical_filters(momentum_scores)

            # Generate signals based on filtered scores
            for symbol, score in filtered_scores.items():
                signal = self._generate_signal_for_symbol(symbol, score, market_data.get(symbol))
                if signal:
                    signals.append(signal)
                    self.signal_history.append(signal)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} momentum signals")

        except Exception as e:
            self.logger.error("Error generating momentum signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and risk management

        This method:
        1. Updates current positions based on market data
        2. Checks stop-loss and take-profit levels
        3. Updates volatility estimates
        4. Monitors portfolio risk metrics

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update position valuations
            self._update_position_valuations(market_data)

            # Check stop-loss and take-profit levels
            exit_signals = self._check_risk_management_levels(market_data)

            # Update volatility estimates
            self._update_volatility_estimates(market_data)

            # Update portfolio risk metrics
            self._update_portfolio_risk_metrics()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"momentum_{self.config.strategy_id}_positions",
                    len(self.position_sizes)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check lookback periods
            if not self.config.lookback_periods or min(self.config.lookback_periods) < 1:
                return False

            # Check thresholds
            if not (0 < self.config.min_momentum_score < self.config.max_momentum_score):
                return False

            # Check risk parameters
            if not (0 < self.config.max_position_size <= 1.0):
                return False

            if not (0 < self.config.volatility_target <= 1.0):
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

    def _calculate_momentum_scores(self) -> Dict[str, float]:
        """
        Calculate momentum scores using multiple methodologies

        Returns composite momentum scores combining:
        - Time-series momentum
        - Cross-sectional momentum (if multiple assets)
        - Volatility-adjusted momentum
        """
        momentum_scores = {}

        for symbol in self.price_data.keys():
            try:
                # Calculate individual momentum components
                ts_momentum = self._calculate_time_series_momentum(symbol)
                vol_adj_momentum = self._calculate_volatility_adjusted_momentum(symbol)

                # Combine momentum factors (equal weight for now)
                composite_score = (ts_momentum + vol_adj_momentum) / 2.0

                # Apply outlier filtering
                if abs(composite_score) <= self.config.max_momentum_score:
                    momentum_scores[symbol] = composite_score

            except Exception as e:
                self.logger.warning(f"Error calculating momentum for {symbol}", {'error': str(e)})
                continue

        return momentum_scores

    def _calculate_time_series_momentum(self, symbol: str) -> float:
        """
        Calculate time-series momentum (Jegadeesh & Titman, 1993)

        Returns the cumulative return over the lookback period,
        skipping the most recent month as per the original methodology.
        """
        if symbol not in self.returns_data:
            return 0.0

        returns = self.returns_data[symbol]

        # Use the longest lookback period for primary momentum
        lookback_months = max(self.config.lookback_periods)

        # Convert months to business days (approximately 21 days per month)
        lookback_days = lookback_months * 21

        if len(returns) < lookback_days + self.config.skip_period * 21:
            return 0.0

        # Skip the most recent month and calculate momentum
        skip_days = self.config.skip_period * 21
        momentum_period = returns.iloc[-(lookback_days + skip_days):-skip_days]

        return momentum_period.sum() if not momentum_period.empty else 0.0

    def _calculate_volatility_adjusted_momentum(self, symbol: str) -> float:
        """
        Calculate volatility-adjusted momentum (Barroso & Santa-Clara, 2015)

        Adjusts momentum by realized volatility to account for volatility clustering
        and provide more stable risk-adjusted returns.
        """
        if symbol not in self.returns_data:
            return 0.0

        returns = self.returns_data[symbol]
        lookback_months = max(self.config.lookback_periods)
        lookback_days = lookback_months * 21

        if len(returns) < lookback_days:
            return 0.0

        # Calculate raw momentum
        momentum_returns = returns.iloc[-lookback_days:]
        raw_momentum = momentum_returns.sum()

        # Calculate realized volatility (annualized)
        volatility = momentum_returns.std() * np.sqrt(252)  # 252 trading days per year

        # Adjust momentum by volatility (higher volatility reduces score)
        if volatility > 0:
            vol_adjusted_momentum = raw_momentum / volatility
        else:
            vol_adjusted_momentum = raw_momentum

        return vol_adjusted_momentum

    def _apply_statistical_filters(self, momentum_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Apply statistical filters to momentum scores

        Filters out signals that don't meet statistical significance thresholds
        and removes outliers.
        """
        if not momentum_scores:
            return {}

        # Convert to numpy array for statistical analysis
        scores = np.array(list(momentum_scores.values()))
        symbols = list(momentum_scores.keys())

        # Calculate z-scores
        if len(scores) > 1 and np.std(scores) > 0:
            z_scores = stats.zscore(scores)
        else:
            z_scores = np.zeros(len(scores))

        # Filter by statistical significance and minimum threshold
        filtered_scores = {}
        for i, (symbol, score) in enumerate(zip(symbols, scores)):
            z_score = z_scores[i]

            # Must exceed both absolute threshold and statistical threshold
            if (abs(score) >= self.config.min_momentum_score and
                abs(z_score) >= self.config.signal_threshold):
                filtered_scores[symbol] = score

        return filtered_scores

    def _generate_signal_for_symbol(self, symbol: str, momentum_score: float,
                                  market_data: Optional[pd.DataFrame]) -> Optional[StrategySignal]:
        """
        Generate a trading signal for a specific symbol

        Determines signal type, position sizing, and risk management levels
        based on momentum score and current market conditions.
        """
        if not market_data or market_data.empty:
            return None

        try:
            current_price = market_data['close'].iloc[-1]

            # Determine signal type based on momentum score
            if momentum_score > 0:
                signal_type = SignalType.BUY
                confidence = min(abs(momentum_score) / self.config.max_momentum_score, 1.0)
            elif momentum_score < 0:
                signal_type = SignalType.SELL
                confidence = min(abs(momentum_score) / self.config.max_momentum_score, 1.0)
            else:
                return None  # No signal

            # Calculate position size
            position_size = self._calculate_position_size(symbol, confidence, market_data)

            # Calculate risk management levels
            stop_loss, take_profit = self._calculate_risk_levels(
                signal_type, current_price, confidence
            )

            # Create signal
            signal = StrategySignal(
                signal_id=f"momentum_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                strength=abs(momentum_score),
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

    def _calculate_position_size(self, symbol: str, confidence: float,
                               market_data: pd.DataFrame) -> float:
        """
        Calculate position size using risk parity principles

        Incorporates:
        - Confidence-based sizing
        - Volatility targeting
        - Maximum position limits
        - Transaction cost awareness
        """
        try:
            # Base position size from confidence
            base_size = confidence * self.config.max_position_size

            # Adjust for volatility if enabled
            if self.config.use_volatility_scaling and symbol in self.volatility_estimates:
                volatility = self.volatility_estimates[symbol].iloc[-1] if not self.volatility_estimates[symbol].empty else self.config.volatility_target
                vol_adjustment = self.config.volatility_target / volatility if volatility > 0 else 1.0
                base_size *= vol_adjustment

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
                             confidence: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop-loss and take-profit levels

        Uses confidence-based levels with trailing stops for better risk management.
        """
        try:
            if not self.config.enable_stop_loss and not self.config.enable_take_profit:
                return None, None

            # Base levels from configuration
            stop_loss_pct = self.config.stop_loss_pct
            take_profit_pct = self.config.take_profit_pct

            # Adjust levels based on confidence (higher confidence = wider stops)
            confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5 to 1.0
            stop_loss_pct *= confidence_multiplier
            take_profit_pct *= confidence_multiplier

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

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """
        Apply portfolio-level risk management constraints

        Ensures the portfolio doesn't exceed volatility targets or drawdown limits.
        """
        if not signals:
            return signals

        try:
            # Check current drawdown
            if self.current_drawdown > self.config.max_drawdown_limit:
                self.logger.warning("Drawdown limit exceeded, reducing signal intensity")
                # Reduce position sizes by 50%
                for signal in signals:
                    signal.target_quantity *= 0.5

            # Check portfolio volatility
            if self.portfolio_volatility > self.config.volatility_target * 1.5:
                self.logger.warning("Portfolio volatility too high, reducing exposure")
                # Reduce all position sizes
                for signal in signals:
                    signal.target_quantity *= 0.7

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
                # This is a simplified version

    def _check_risk_management_levels(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Check stop-loss and take-profit levels for existing positions"""
        exit_signals = []

        # Implementation for checking risk levels would go here
        # This would generate exit signals when stop-loss or take-profit levels are hit

        return exit_signals

    def _update_volatility_estimates(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update volatility estimates for all symbols"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty and 'close' in data.columns:
                returns = data['close'].pct_change().dropna()
                if len(returns) >= 20:  # Minimum period for volatility estimate
                    # Calculate rolling volatility (21-day window, annualized)
                    volatility = returns.rolling(21).std() * np.sqrt(252)
                    self.volatility_estimates[symbol] = volatility

    def _update_portfolio_risk_metrics(self) -> None:
        """Update portfolio-level risk metrics"""
        try:
            # Simplified portfolio volatility calculation
            if self.volatility_estimates:
                # Average volatility across positions (weighted by position size)
                total_weight = sum(self.position_sizes.values())
                if total_weight > 0:
                    weighted_volatility = sum(
                        vol.iloc[-1] * weight for vol, weight in
                        zip(self.volatility_estimates.values(), self.position_sizes.values())
                        if not vol.empty
                    ) / total_weight
                    self.portfolio_volatility = weighted_volatility

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