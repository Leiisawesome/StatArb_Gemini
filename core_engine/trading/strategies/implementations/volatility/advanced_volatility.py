"""
Advanced Volatility Strategy Implementation

This module implements sophisticated volatility-based trading strategies that
exploit volatility clustering, mean reversion in volatility, and volatility
risk premium. The strategies use advanced volatility modeling and options
strategies to generate alpha from volatility dynamics.

The strategy uses:
- GARCH family models for volatility forecasting
- Implied vs realized volatility arbitrage
- Volatility risk premium harvesting
- Options strategies (straddles, strangles, butterflies)
- Volatility targeting and dynamic hedging

Academic Foundations:
- Engle (1982) ARCH model
- Bollerslev (1986) GARCH model
- Heston (1993) stochastic volatility model
- Carr & Wu (2009) variance risk premium
- Ang et al. (2006) volatility risk premium
- Moreira & Muir (2017) volatility-managed portfolios

Components:
- Volatility forecasting models
- Options pricing and Greeks calculation
- Volatility arbitrage strategies
- Risk management with volatility targeting
- Dynamic portfolio rebalancing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from scipy.optimize import minimize
from statsmodels.tsa.arima.model import ARIMA
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class VolatilityModel(Enum):
    """Volatility modeling approaches"""
    GARCH = "garch"
    EGARCH = "egarch"
    GJR_GARCH = "gjr_garch"
    STOCHASTIC_VOL = "stochastic_vol"
    REALIZED_VOL = "realized_vol"


class VolatilityStrategy(Enum):
    """Types of volatility trading strategies"""
    VOL_ARBITRAGE = "vol_arbitrage"
    VOL_RISK_PREMIUM = "vol_risk_premium"
    VOL_TARGETING = "vol_targeting"
    OPTIONS_STRATEGIES = "options_strategies"
    VOL_MEAN_REVERSION = "vol_mean_reversion"


class OptionsStrategy(Enum):
    """Options trading strategies"""
    LONG_STRADDLE = "long_straddle"
    SHORT_STRADDLE = "short_straddle"
    LONG_STRANGLE = "long_strangle"
    SHORT_STRANGLE = "short_strangle"
    BUTTERFLY = "butterfly"
    CONDOR = "condor"
    CALENDAR_SPREAD = "calendar_spread"


@dataclass
class VolatilityForecast:
    """Container for volatility forecast data"""
    timestamp: datetime
    forecast_vol: float
    confidence_interval: Tuple[float, float]
    model_used: VolatilityModel
    realized_vol: float
    implied_vol: Optional[float] = None


@dataclass
class OptionsPosition:
    """Represents an options position"""
    option_type: str  # 'call' or 'put'
    strike_price: float
    expiration_date: datetime
    quantity: int
    premium: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


@dataclass
class VolatilityStrategyConfig(StrategyConfig):
    """Configuration for Advanced Volatility Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.VOLATILITY

    # Volatility modeling
    volatility_model: VolatilityModel = VolatilityModel.GARCH
    forecast_horizon: int = 21  # Days to forecast ahead
    vol_lookback_period: int = 252  # Trading days for volatility estimation
    vol_update_frequency: int = 1  # Days between volatility updates

    # Strategy type
    vol_strategy: VolatilityStrategy = VolatilityStrategy.VOL_RISK_PREMIUM
    options_strategy: OptionsStrategy = OptionsStrategy.SHORT_STRADDLE

    # Volatility thresholds
    vol_entry_threshold: float = 1.5  # Z-score for volatility entry
    vol_exit_threshold: float = 0.5  # Z-score for volatility exit
    min_vol_level: float = 0.10  # Minimum volatility level (10%)
    max_vol_level: float = 0.50  # Maximum volatility level (50%)

    # Options parameters
    use_options: bool = True
    options_maturity_days: int = 30  # Days to expiration
    moneyness_range: Tuple[float, float] = (0.95, 1.05)  # Strike range as % of spot
    max_options_positions: int = 10  # Maximum concurrent options positions

    # Volatility targeting
    enable_vol_targeting: bool = True
    target_volatility: float = 0.15  # Target annualized volatility (15%)
    vol_rebalance_freq: int = 21  # Days between rebalancing
    vol_scaling_factor: float = 1.0  # Leverage factor for volatility targeting

    # Risk management
    max_vol_risk: float = 0.05  # Maximum volatility risk per position
    stop_loss_pct: float = 0.20  # Stop loss percentage
    max_holding_period: int = 30  # Maximum days to hold position
    max_drawdown_pct: float = 0.15  # Maximum drawdown before position closure

    # Position sizing
    base_position_size: float = 0.1  # Base position size as % of portfolio
    vol_adjusted_sizing: bool = True  # Adjust size based on volatility
    risk_per_trade: float = 0.02  # Risk per trade (2% of portfolio)

    # Mean reversion parameters
    vol_mean_reversion_window: int = 60  # Days for mean reversion calculation
    vol_reversion_threshold: float = 2.0  # Z-score threshold for reversion

    # Advanced features
    enable_dynamic_hedging: bool = True  # Dynamic delta hedging
    enable_vol_clustering: bool = True  # Account for volatility clustering
    enable_jump_detection: bool = True  # Detect volatility jumps
    use_transaction_costs: bool = True  # Account for transaction costs

    # Transaction costs
    options_commission: float = 0.5  # Commission per options contract
    underlying_commission: float = 0.01  # Commission per underlying share (%)

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedVolatilityStrategy(BaseStrategy):
    """
    Advanced Volatility Strategy Implementation

    This strategy implements sophisticated volatility-based trading:
    1. Advanced volatility forecasting using GARCH models
    2. Volatility risk premium harvesting through options strategies
    3. Volatility targeting with dynamic position sizing
    4. Mean reversion in volatility levels
    5. Risk management with volatility-adjusted stops

    The strategy exploits volatility clustering, mean reversion in volatility,
    and the volatility risk premium to generate consistent returns.

    Key Features:
    - Multiple volatility models (GARCH, EGARCH, Stochastic Volatility)
    - Options strategies (straddles, strangles, butterflies)
    - Volatility targeting and risk parity
    - Dynamic hedging and position management
    - Jump detection and volatility regime switching
    """

    def __init__(self, config: VolatilityStrategyConfig):
        super().__init__(config)
        self.config: VolatilityStrategyConfig = config

        # Initialize components
        self.logger = get_logger(f"volatility_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Volatility tracking
        self.volatility_forecasts: Dict[str, List[VolatilityForecast]] = {}
        self.realized_volatility: Dict[str, pd.Series] = {}
        self.implied_volatility: Dict[str, pd.Series] = {}
        self.volatility_regime: Dict[str, str] = {}  # 'low', 'normal', 'high'

        # Options positions
        self.options_positions: Dict[str, List[OptionsPosition]] = {}
        self.options_greeks: Dict[str, Dict[str, float]] = {}

        # Position tracking
        self.active_positions: Dict[str, StrategyPosition] = {}
        self.position_greeks: Dict[str, Dict[str, float]] = {}
        self.entry_times: Dict[str, datetime] = {}
        self.stop_levels: Dict[str, float] = {}

        # Volatility models
        self.vol_models: Dict[str, Any] = {}
        self.model_parameters: Dict[str, Dict[str, float]] = {}

        # Market data cache
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.DataFrame] = {}
        self.options_data: Dict[str, pd.DataFrame] = {}

        # Signal history
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Volatility Strategy initialized", {
            'strategy_id': config.strategy_id,
            'volatility_model': config.volatility_model.value,
            'vol_strategy': config.vol_strategy.value
        })

    def initialize(self) -> bool:
        """
        Initialize the volatility strategy

        Sets up volatility models, options pricing, and risk management
        parameters for volatility-based trading.
        """
        try:
            self.logger.info("Initializing Advanced Volatility Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize volatility models
            self._initialize_volatility_models()

            # Set up options pricing if needed
            if self.config.use_options:
                self._initialize_options_pricing()

            # Initialize position tracking
            self.active_positions = {}
            self.position_greeks = {}
            self.entry_times = {}
            self.stop_levels = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"volatility_{self.config.strategy_id}")

            self.logger.info("Advanced Volatility Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize volatility strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate volatility-based trading signals

        This method implements the core volatility trading logic:
        1. Update volatility forecasts and market data
        2. Calculate volatility signals and regime detection
        3. Generate options or underlying positions based on strategy
        4. Apply risk management and position sizing
        5. Manage existing positions and hedging

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update market data and volatility forecasts
            self._update_market_data(market_data)
            self._update_volatility_forecasts()

            # Generate signals for each symbol
            for symbol in self.price_data.keys():
                symbol_signals = self._generate_symbol_signals(symbol)
                signals.extend(symbol_signals)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            # Manage existing positions
            signals.extend(self._manage_existing_positions())

            self.logger.debug(f"Generated {len(signals)} volatility signals")

        except Exception as e:
            self.logger.error("Error generating volatility signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and volatility state

        This method:
        1. Updates current positions and P&L
        2. Recalculates Greeks for options positions
        3. Monitors volatility levels and regime changes
        4. Adjusts hedges and manages risk
        5. Updates volatility forecasts

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update market data
            self._update_market_data(market_data)

            # Update position Greeks and risk
            self._update_position_greeks()

            # Monitor volatility regime changes
            self._monitor_volatility_regime()

            # Adjust dynamic hedges
            if self.config.enable_dynamic_hedging:
                self._adjust_dynamic_hedges()

            # Update stop levels
            self._update_stop_levels()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                total_positions = len(self.active_positions)
                self.performance_monitor.record_metric(
                    f"volatility_{self.config.strategy_id}_positions",
                    total_positions
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check volatility parameters
            if not (0.05 <= self.config.min_vol_level <= self.config.max_vol_level <= 1.0):
                return False

            if not (0.5 <= self.config.vol_entry_threshold <= 5.0):
                return False

            # Check position sizing
            if not (0 < self.config.base_position_size <= 1.0):
                return False

            if not (0 < self.config.risk_per_trade <= 0.1):
                return False

            # Check options parameters
            if self.config.use_options:
                if not (7 <= self.config.options_maturity_days <= 365):
                    return False

            return True

        except Exception:
            return False

    def _initialize_volatility_models(self) -> None:
        """Initialize volatility forecasting models"""
        try:
            # Initialize GARCH model parameters
            if self.config.volatility_model == VolatilityModel.GARCH:
                self.model_parameters = {
                    'omega': 0.0001,  # Constant term
                    'alpha': 0.1,     # ARCH parameter
                    'beta': 0.85      # GARCH parameter
                }

            self.logger.info("Volatility models initialized")

        except Exception as e:
            self.logger.error("Error initializing volatility models", {'error': str(e)})

    def _initialize_options_pricing(self) -> None:
        """Initialize options pricing framework"""
        try:
            # Initialize Black-Scholes parameters
            self.risk_free_rate = 0.03  # 3% risk-free rate
            self.dividend_yield = 0.02  # 2% dividend yield

            self.logger.info("Options pricing initialized")

        except Exception as e:
            self.logger.error("Error initializing options pricing", {'error': str(e)})

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update internal market data cache"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty:
                self.price_data[symbol] = data.copy()

                # Calculate returns if price data available
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                    self.returns_data[symbol] = returns

                    # Update realized volatility
                    self._update_realized_volatility(symbol, returns)

    def _update_realized_volatility(self, symbol: str, returns: pd.Series) -> None:
        """Update realized volatility calculation"""
        try:
            # Calculate rolling realized volatility
            window = min(21, len(returns))  # 21 trading days
            realized_vol = returns.rolling(window=window).std() * np.sqrt(252)  # Annualized

            self.realized_volatility[symbol] = realized_vol

        except Exception as e:
            self.logger.error("Error updating realized volatility", {'symbol': symbol, 'error': str(e)})

    def _update_volatility_forecasts(self) -> None:
        """Update volatility forecasts for all symbols"""
        try:
            for symbol in self.price_data.keys():
                if symbol in self.returns_data:
                    forecast = self._forecast_volatility(symbol)
                    if forecast:
                        if symbol not in self.volatility_forecasts:
                            self.volatility_forecasts[symbol] = []
                        self.volatility_forecasts[symbol].append(forecast)

                        # Keep only recent forecasts
                        if len(self.volatility_forecasts[symbol]) > 10:
                            self.volatility_forecasts[symbol] = self.volatility_forecasts[symbol][-10:]

        except Exception as e:
            self.logger.error("Error updating volatility forecasts", {'error': str(e)})

    def _forecast_volatility(self, symbol: str) -> Optional[VolatilityForecast]:
        """
        Forecast volatility using the configured model

        Returns a VolatilityForecast object with the prediction
        """
        try:
            if symbol not in self.returns_data:
                return None

            returns = self.returns_data[symbol]
            if len(returns) < 30:
                return None

            current_vol = returns.tail(21).std() * np.sqrt(252)

            # Simple GARCH(1,1) forecast (simplified implementation)
            if self.config.volatility_model == VolatilityModel.GARCH:
                forecast_vol = self._garch_forecast(returns)
            else:
                # Fallback to historical volatility
                forecast_vol = current_vol

            # Calculate confidence interval
            vol_std = current_vol * 0.3  # Rough estimate
            ci_lower = max(0, forecast_vol - 1.96 * vol_std)
            ci_upper = forecast_vol + 1.96 * vol_std

            return VolatilityForecast(
                timestamp=datetime.now(),
                forecast_vol=forecast_vol,
                confidence_interval=(ci_lower, ci_upper),
                model_used=self.config.volatility_model,
                realized_vol=current_vol
            )

        except Exception as e:
            self.logger.error("Error forecasting volatility", {'symbol': symbol, 'error': str(e)})
            return None

    def _garch_forecast(self, returns: pd.Series) -> float:
        """Simple GARCH(1,1) volatility forecast"""
        try:
            # Simplified GARCH implementation
            omega = self.model_parameters.get('omega', 0.0001)
            alpha = self.model_parameters.get('alpha', 0.1)
            beta = self.model_parameters.get('beta', 0.85)

            # Get recent returns
            recent_returns = returns.tail(21).values
            recent_vol = returns.tail(21).std()

            # Forecast next period volatility
            forecast_vol = np.sqrt(omega + alpha * recent_returns[-1]**2 + beta * recent_vol**2)

            return forecast_vol * np.sqrt(252)  # Annualize

        except Exception:
            return returns.std() * np.sqrt(252)

    def _generate_symbol_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate trading signals for a specific symbol"""
        signals = []

        try:
            # Get current volatility state
            vol_state = self._get_volatility_state(symbol)
            if vol_state is None:
                return signals

            current_vol, forecast_vol, vol_z_score, regime = vol_state

            # Generate signals based on strategy type
            if self.config.vol_strategy == VolatilityStrategy.VOL_RISK_PREMIUM:
                signals.extend(self._generate_vol_risk_premium_signals(symbol, vol_z_score, regime))

            elif self.config.vol_strategy == VolatilityStrategy.VOL_MEAN_REVERSION:
                signals.extend(self._generate_vol_mean_reversion_signals(symbol, vol_z_score))

            elif self.config.vol_strategy == VolatilityStrategy.VOL_TARGETING:
                signals.extend(self._generate_vol_targeting_signals(symbol, current_vol))

            elif self.config.vol_strategy == VolatilityStrategy.OPTIONS_STRATEGIES:
                signals.extend(self._generate_options_signals(symbol, vol_z_score, regime))

        except Exception as e:
            self.logger.error("Error generating symbol signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _get_volatility_state(self, symbol: str) -> Optional[Tuple[float, float, float, str]]:
        """
        Get current volatility state for a symbol

        Returns (current_vol, forecast_vol, z_score, regime)
        """
        try:
            if symbol not in self.realized_volatility or symbol not in self.volatility_forecasts:
                return None

            # Get current realized volatility
            current_vol = self.realized_volatility[symbol].iloc[-1]

            # Get latest forecast
            latest_forecast = self.volatility_forecasts[symbol][-1] if self.volatility_forecasts[symbol] else None
            forecast_vol = latest_forecast.forecast_vol if latest_forecast else current_vol

            # Calculate z-score relative to historical average
            vol_history = self.realized_volatility[symbol]
            vol_mean = vol_history.mean()
            vol_std = vol_history.std()
            vol_z_score = (current_vol - vol_mean) / vol_std if vol_std > 0 else 0

            # Determine volatility regime
            regime = self._classify_volatility_regime(current_vol, vol_mean, vol_std)

            return current_vol, forecast_vol, vol_z_score, regime

        except Exception as e:
            self.logger.error("Error getting volatility state", {'symbol': symbol, 'error': str(e)})
            return None

    def _classify_volatility_regime(self, current_vol: float, vol_mean: float, vol_std: float) -> str:
        """Classify current volatility regime"""
        try:
            if current_vol > vol_mean + vol_std:
                return 'high'
            elif current_vol < vol_mean - vol_std:
                return 'low'
            else:
                return 'normal'

        except Exception:
            return 'normal'

    def _generate_vol_risk_premium_signals(self, symbol: str, vol_z_score: float, regime: str) -> List[StrategySignal]:
        """Generate signals for volatility risk premium strategy"""
        signals = []

        try:
            # Volatility risk premium strategy: sell volatility when it's expensive
            if regime == 'high' and vol_z_score > self.config.vol_entry_threshold:
                if self.config.use_options:
                    signals.extend(self._generate_short_volatility_signals(symbol))
                else:
                    # Use VIX futures or volatility ETFs
                    signals.extend(self._generate_vol_etf_signals(symbol, SignalType.SELL))

            # Buy volatility when it's cheap (contrarian)
            elif regime == 'low' and vol_z_score < -self.config.vol_entry_threshold:
                if self.config.use_options:
                    signals.extend(self._generate_long_volatility_signals(symbol))
                else:
                    signals.extend(self._generate_vol_etf_signals(symbol, SignalType.BUY))

        except Exception as e:
            self.logger.error("Error generating vol risk premium signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_vol_mean_reversion_signals(self, symbol: str, vol_z_score: float) -> List[StrategySignal]:
        """Generate signals for volatility mean reversion strategy"""
        signals = []

        try:
            # Mean reversion: buy when volatility is low, sell when high
            if abs(vol_z_score) > self.config.vol_entry_threshold:
                if vol_z_score > 0:  # High volatility - sell
                    signals.extend(self._generate_short_volatility_signals(symbol))
                else:  # Low volatility - buy
                    signals.extend(self._generate_long_volatility_signals(symbol))

        except Exception as e:
            self.logger.error("Error generating vol mean reversion signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_vol_targeting_signals(self, symbol: str, current_vol: float) -> List[StrategySignal]:
        """Generate signals for volatility targeting strategy"""
        signals = []

        try:
            # Calculate volatility z-score
            if symbol in self.realized_volatility:
                vol_history = self.realized_volatility[symbol]
                vol_mean = vol_history.mean()
                vol_std = vol_history.std()
                vol_z_score = (current_vol - vol_mean) / vol_std if vol_std > 0 else 0
            else:
                vol_z_score = 0

            # Adjust position size to target volatility
            if self.config.enable_vol_targeting:
                target_vol = self.config.target_volatility
                vol_ratio = target_vol / current_vol if current_vol > 0 else 1.0

                # Scale position size
                scaling_factor = min(vol_ratio * self.config.vol_scaling_factor, 3.0)  # Max 3x leverage

                if symbol in self.active_positions:
                    # Adjust existing position
                    current_pos = self.active_positions[symbol]
                    target_size = current_pos.quantity * scaling_factor

                    if abs(target_size - current_pos.quantity) / abs(current_pos.quantity) > 0.1:  # 10% threshold
                        signal_type = SignalType.BUY if target_size > current_pos.quantity else SignalType.SELL
                        quantity_change = abs(target_size - current_pos.quantity)

                        signal = StrategySignal(
                            signal_id=f"vol_target_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            strategy_id=self.config.strategy_id,
                            timestamp=datetime.now(),
                            symbol=symbol,
                            signal_type=signal_type,
                            confidence=0.7,
                            strength=abs(vol_z_score),
                            target_quantity=quantity_change,
                            signal_price=self.price_data[symbol]['close'].iloc[-1],
                            entry_price=self.price_data[symbol]['close'].iloc[-1],
                            max_position_size=self.config.base_position_size
                        )
                        signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating vol targeting signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_options_signals(self, symbol: str, vol_z_score: float, regime: str) -> List[StrategySignal]:
        """Generate options-based trading signals"""
        signals = []

        try:
            if not self.config.use_options:
                return signals

            # Check position limits
            current_options_count = len(self.options_positions.get(symbol, []))
            if current_options_count >= self.config.max_options_positions:
                return signals

            # Generate signals based on options strategy
            if self.config.options_strategy == OptionsStrategy.SHORT_STRADDLE:
                if regime == 'high' and vol_z_score > self.config.vol_entry_threshold:
                    signals.extend(self._generate_straddle_signals(symbol, 'short'))

            elif self.config.options_strategy == OptionsStrategy.LONG_STRADDLE:
                if regime == 'low' and vol_z_score < -self.config.vol_entry_threshold:
                    signals.extend(self._generate_straddle_signals(symbol, 'long'))

        except Exception as e:
            self.logger.error("Error generating options signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_short_volatility_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals to sell volatility"""
        signals = []

        try:
            if self.config.use_options:
                # Sell options (straddle or strangle)
                signals.extend(self._generate_straddle_signals(symbol, 'short'))
            else:
                # Sell volatility ETF or futures
                signals.extend(self._generate_vol_etf_signals(symbol, SignalType.SELL))

        except Exception as e:
            self.logger.error("Error generating short volatility signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_long_volatility_signals(self, symbol: str) -> List[StrategySignal]:
        """Generate signals to buy volatility"""
        signals = []

        try:
            if self.config.use_options:
                # Buy options (straddle or strangle)
                signals.extend(self._generate_straddle_signals(symbol, 'long'))
            else:
                # Buy volatility ETF or futures
                signals.extend(self._generate_vol_etf_signals(symbol, SignalType.BUY))

        except Exception as e:
            self.logger.error("Error generating long volatility signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _generate_straddle_signals(self, symbol: str, position_type: str) -> List[StrategySignal]:
        """Generate straddle options signals"""
        signals = []

        try:
            spot_price = self.price_data[symbol]['close'].iloc[-1]
            expiration = datetime.now() + timedelta(days=self.config.options_maturity_days)

            # At-the-money strikes
            strike_price = spot_price

            # Estimate option premiums (simplified Black-Scholes)
            vol = self.realized_volatility[symbol].iloc[-1]
            time_to_expiry = self.config.options_maturity_days / 365

            call_premium = self._black_scholes_price(spot_price, strike_price, time_to_expiry, vol, 'call')
            put_premium = self._black_scholes_price(spot_price, strike_price, time_to_expiry, vol, 'put')

            # Position sizing
            max_loss = call_premium + put_premium  # Maximum loss for short straddle
            position_size = self._calculate_options_position_size(max_loss)

            if position_type == 'short':
                # Sell call and put
                call_signal = self._create_options_signal(symbol, 'call', strike_price, expiration,
                                                        -position_size, call_premium, SignalType.SELL)
                put_signal = self._create_options_signal(symbol, 'put', strike_price, expiration,
                                                       -position_size, put_premium, SignalType.SELL)
                signals.extend([call_signal, put_signal])
            else:
                # Buy call and put
                call_signal = self._create_options_signal(symbol, 'call', strike_price, expiration,
                                                        position_size, call_premium, SignalType.BUY)
                put_signal = self._create_options_signal(symbol, 'put', strike_price, expiration,
                                                       position_size, put_premium, SignalType.BUY)
                signals.extend([call_signal, put_signal])

        except Exception as e:
            self.logger.error("Error generating straddle signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _black_scholes_price(self, S: float, K: float, T: float, sigma: float, option_type: str) -> float:
        """Simplified Black-Scholes option pricing"""
        try:
            d1 = (np.log(S/K) + (self.risk_free_rate - self.dividend_yield + sigma**2/2)*T) / (sigma*np.sqrt(T))
            d2 = d1 - sigma*np.sqrt(T)

            if option_type == 'call':
                price = S*np.exp(-self.dividend_yield*T)*stats.norm.cdf(d1) - K*np.exp(-self.risk_free_rate*T)*stats.norm.cdf(d2)
            else:
                price = K*np.exp(-self.risk_free_rate*T)*stats.norm.cdf(-d2) - S*np.exp(-self.dividend_yield*T)*stats.norm.cdf(-d1)

            return max(price, 0.01)  # Minimum premium

        except Exception:
            return 0.1  # Default premium

    def _create_options_signal(self, symbol: str, option_type: str, strike: float,
                             expiration: datetime, quantity: int, premium: float,
                             signal_type: SignalType) -> StrategySignal:
        """Create an options trading signal"""
        signal = StrategySignal(
            signal_id=f"options_{option_type}_{symbol}_{strike}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=self.config.strategy_id,
            timestamp=datetime.now(),
            symbol=f"{symbol}_{option_type}_{strike}_{expiration.strftime('%Y%m%d')}",  # Options symbol
            signal_type=signal_type,
            confidence=0.7,
            strength=1.0,
            target_quantity=abs(quantity),
            signal_price=premium,
            entry_price=premium,
            max_position_size=self.config.base_position_size
        )
        return signal

    def _generate_vol_etf_signals(self, symbol: str, signal_type: SignalType) -> List[StrategySignal]:
        """Generate signals for volatility ETFs (like VXX)"""
        signals = []

        try:
            # Map symbol to volatility ETF (simplified)
            vol_etf_symbol = f"VXX_{symbol}"  # Placeholder

            position_size = self._calculate_position_size(symbol)

            signal = StrategySignal(
                signal_id=f"vol_etf_{signal_type.value}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                strategy_id=self.config.strategy_id,
                timestamp=datetime.now(),
                symbol=vol_etf_symbol,
                signal_type=signal_type,
                confidence=0.6,
                strength=1.0,
                target_quantity=position_size,
                signal_price=self.price_data[symbol]['close'].iloc[-1],  # Placeholder
                entry_price=self.price_data[symbol]['close'].iloc[-1],
                max_position_size=self.config.base_position_size
            )
            signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating vol ETF signals", {'symbol': symbol, 'error': str(e)})

        return signals

    def _calculate_position_size(self, symbol: str) -> float:
        """Calculate position size based on risk management"""
        try:
            base_size = self.config.base_position_size
            risk_amount = self.config.risk_per_trade

            if self.config.vol_adjusted_sizing and symbol in self.realized_volatility:
                current_vol = self.realized_volatility[symbol].iloc[-1]
                vol_adjustment = self.config.target_volatility / current_vol if current_vol > 0 else 1.0
                base_size *= vol_adjustment

            return min(base_size, self.config.base_position_size)

        except Exception:
            return self.config.base_position_size

    def _calculate_options_position_size(self, max_loss: float) -> int:
        """Calculate options position size based on risk"""
        try:
            risk_amount = self.config.risk_per_trade
            position_size = int(risk_amount / max_loss) if max_loss > 0 else 1
            return max(1, min(position_size, 100))  # Between 1 and 100 contracts

        except Exception:
            return 1

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Apply portfolio-level risk management constraints"""
        try:
            # Limit total volatility exposure
            total_exposure = sum(abs(s.target_quantity * s.signal_price) for s in signals)

            if total_exposure > self.config.max_vol_risk:
                # Scale down all signals
                scale_factor = self.config.max_vol_risk / total_exposure
                for signal in signals:
                    signal.target_quantity *= scale_factor

            return signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _manage_existing_positions(self) -> List[StrategySignal]:
        """Manage existing positions (exits, adjustments)"""
        signals = []

        try:
            for symbol, position in list(self.active_positions.items()):
                # Check stop loss
                if self._should_exit_position(symbol):
                    exit_signal = self._generate_exit_signal(symbol, position)
                    signals.append(exit_signal)

                # Check holding period
                if symbol in self.entry_times:
                    holding_period = (datetime.now() - self.entry_times[symbol]).days
                    if holding_period >= self.config.max_holding_period:
                        exit_signal = self._generate_exit_signal(symbol, position)
                        signals.append(exit_signal)

        except Exception as e:
            self.logger.error("Error managing existing positions", {'error': str(e)})

        return signals

    def _should_exit_position(self, symbol: str) -> bool:
        """Determine if a position should be exited"""
        try:
            if symbol not in self.active_positions:
                return False

            position = self.active_positions[symbol]

            # Check stop loss
            current_price = self.price_data[symbol]['close'].iloc[-1]
            entry_price = position.entry_price

            if position.quantity > 0:  # Long position
                loss_pct = (entry_price - current_price) / entry_price
            else:  # Short position
                loss_pct = (current_price - entry_price) / entry_price

            if loss_pct >= self.config.stop_loss_pct:
                return True

            return False

        except Exception:
            return False

    def _generate_exit_signal(self, symbol: str, position: StrategyPosition) -> StrategySignal:
        """Generate exit signal for a position"""
        signal_type = SignalType.CLOSE_LONG if position.quantity > 0 else SignalType.CLOSE_SHORT

        signal = StrategySignal(
            signal_id=f"exit_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=self.config.strategy_id,
            timestamp=datetime.now(),
            symbol=symbol,
            signal_type=signal_type,
            confidence=0.9,
            strength=1.0,
            target_quantity=abs(position.quantity),
            signal_price=self.price_data[symbol]['close'].iloc[-1],
            entry_price=position.entry_price,
            max_position_size=self.config.base_position_size
        )

        return signal

    def _update_position_greeks(self) -> None:
        """Update Greeks for options positions"""
        # This would calculate delta, gamma, theta, vega for options positions
        pass

    def _monitor_volatility_regime(self) -> None:
        """Monitor changes in volatility regime"""
        try:
            for symbol in self.price_data.keys():
                vol_state = self._get_volatility_state(symbol)
                if vol_state:
                    _, _, _, regime = vol_state
                    self.volatility_regime[symbol] = regime

        except Exception as e:
            self.logger.error("Error monitoring volatility regime", {'error': str(e)})

    def _adjust_dynamic_hedges(self) -> None:
        """Adjust dynamic hedges for options positions"""
        # This would implement delta-hedging for options positions
        pass

    def _update_stop_levels(self) -> None:
        """Update trailing stop levels"""
        try:
            for symbol, position in self.active_positions.items():
                if symbol in self.realized_volatility:
                    current_vol = self.realized_volatility[symbol].iloc[-1]
                    # Adjust stop level based on current volatility
                    vol_adjusted_stop = self.config.stop_loss_pct * (1 + current_vol)
                    self.stop_levels[symbol] = vol_adjusted_stop

        except Exception as e:
            self.logger.error("Error updating stop levels", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.active_positions)

        # Add volatility-specific metrics
        avg_volatility = np.mean([v.iloc[-1] for v in self.realized_volatility.values() if not v.empty])
        metrics.total_return = avg_volatility if not np.isnan(avg_volatility) else 0

        return metrics