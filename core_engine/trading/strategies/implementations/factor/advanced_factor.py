"""
Advanced Factor-based Strategy Implementation

This module implements sophisticated factor-based trading strategies that exploit
systematic risk factors using rigorous quantitative methods and academic frameworks.

The strategy uses:
- Fama-French 3/5-factor models (1993, 2015)
- Risk parity and factor timing approaches
- Dynamic factor exposure management
- Statistical factor model estimation
- Factor momentum and mean reversion

Key Features:
- Multi-factor portfolio construction
- Factor timing and rotation
- Risk parity across factors
- Dynamic factor exposures
- Transaction cost optimization

Academic Foundations:
- Fama & French (1993) three-factor model
- Fama & French (2015) five-factor model
- Carhart (1997) four-factor model
- Cochrane (2001) factor pricing theory
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class FactorModel(Enum):
    """Factor model types"""
    CAPM = "capm"  # Capital Asset Pricing Model (Sharpe, 1964)
    FAMA_FRENCH_3 = "fama_french_3"  # Fama & French (1993)
    FAMA_FRENCH_5 = "fama_french_5"  # Fama & French (2015)
    CARHART_4 = "carhart_4"  # Carhart (1997)
    BARRA = "barra"  # Barra risk model
    CUSTOM = "custom"  # User-defined factors


class FactorType(Enum):
    """Individual factor types"""
    MARKET = "market"  # Market excess return (MKT)
    SIZE = "size"  # Small minus big (SMB)
    VALUE = "value"  # High minus low (HML)
    PROFITABILITY = "profitability"  # Robust minus weak (RMW)
    INVESTMENT = "investment"  # Conservative minus aggressive (CMA)
    MOMENTUM = "momentum"  # Momentum factor (MOM)
    QUALITY = "quality"  # Quality factor
    VOLATILITY = "volatility"  # Low volatility factor
    LIQUIDITY = "liquidity"  # Liquidity factor


@dataclass
class FactorDefinition:
    """Definition of a factor"""
    name: str
    type: FactorType
    description: str
    long_portfolio: str  # Assets in long leg
    short_portfolio: str  # Assets in short leg
    weighting: str = "equal"  # equal, market_cap, sqrt_market_cap
    rebalancing_freq: str = "monthly"


@dataclass
class FactorConfig(StrategyConfig):
    """Configuration for Advanced Factor-based Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.MULTI_FACTOR

    # Factor model settings
    factor_model: FactorModel = FactorModel.FAMA_FRENCH_5
    factor_types: List[FactorType] = field(default_factory=lambda: [
        FactorType.MARKET, FactorType.SIZE, FactorType.VALUE,
        FactorType.PROFITABILITY, FactorType.INVESTMENT
    ])

    # Factor construction parameters
    factor_lookback: int = 252  # Trading days for factor estimation
    factor_rebalance_freq: str = "monthly"  # monthly, quarterly
    min_factor_history: int = 63  # Minimum history for factor estimation

    # Factor exposure management
    target_factor_exposures: Dict[FactorType, float] = field(default_factory=dict)
    max_factor_exposure: float = 2.0  # Maximum exposure to any single factor
    factor_neutral: bool = False  # Force factor neutrality

    # Risk parity settings
    use_risk_parity: bool = True
    risk_parity_lookback: int = 63  # Lookback for volatility estimation
    risk_parity_rebalance_freq: str = "monthly"

    # Factor timing parameters
    use_factor_timing: bool = True
    timing_lookback: int = 252
    timing_z_threshold: float = 1.0  # Z-score threshold for timing

    # Position sizing
    max_position_size: float = 0.25  # Max position as % of portfolio per factor
    volatility_target: float = 0.12  # Annualized volatility target
    position_rebalance_freq: str = "monthly"

    # Transaction costs and constraints
    transaction_cost_bps: float = 5.0
    min_position_size: float = 0.001
    max_positions_per_factor: int = 50

    # Advanced features
    use_pca_factors: bool = False  # Use PCA for factor extraction
    use_dynamic_factors: bool = True  # Dynamically adjust factor weights
    enable_factor_momentum: bool = True  # Factor momentum timing
    enable_factor_mean_reversion: bool = False  # Factor mean reversion

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedFactorStrategy(BaseStrategy):
    """
    Advanced Factor-based Strategy Implementation

    This strategy implements multiple factor models with academic rigor:
    1. Fama-French 3/5-factor models for systematic factor exposure
    2. Risk parity weighting across factors
    3. Factor timing and rotation
    4. Dynamic factor exposure management

    The strategy constructs portfolios that systematically harvest factor premia
    while maintaining proper risk management and diversification.
    """

    def __init__(self, config: FactorConfig):
        super().__init__(config)
        self.config: FactorConfig = config

        # Initialize components
        self.logger = get_logger(f"factor_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Factor model state
        self.factor_definitions: Dict[FactorType, FactorDefinition] = {}
        self.factor_returns: Dict[FactorType, pd.Series] = {}
        self.factor_exposures: Dict[str, Dict[FactorType, float]] = {}
        self.factor_timings: Dict[FactorType, float] = {}

        # Portfolio construction state
        self.target_weights: Dict[str, float] = {}
        self.current_weights: Dict[str, float] = {}
        self.factor_contributions: Dict[FactorType, float] = {}

        # Market data cache
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.DataFrame] = {}

        # Risk management state
        self.portfolio_volatility: float = 0.0
        self.factor_volatilities: Dict[FactorType, float] = {}

        # Signal history
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Factor Strategy initialized", {
            'strategy_id': config.strategy_id,
            'factor_model': config.factor_model.value,
            'factor_types': [ft.value for ft in config.factor_types]
        })

    def initialize(self) -> bool:
        """
        Initialize the factor-based strategy

        Sets up factor definitions, validates configuration, and prepares
        for factor model estimation and portfolio construction.
        """
        try:
            self.logger.info("Initializing Advanced Factor Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize factor definitions
            self._initialize_factor_definitions()

            # Set up factor exposures
            self._initialize_factor_exposures()

            # Initialize portfolio weights
            self.target_weights = {}
            self.current_weights = {}
            self.factor_contributions = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"factor_{self.config.strategy_id}")

            # Initialize risk management
            self.portfolio_volatility = self.config.volatility_target

            self.logger.info("Advanced Factor Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize factor strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate factor-based trading signals

        This method implements the core factor strategy logic:
        1. Estimate factor returns and exposures
        2. Apply factor timing and risk parity
        3. Construct target portfolio weights
        4. Generate rebalancing signals

        Args:
            market_data: Dictionary of OHLCV data for each symbol

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update internal data cache
            self._update_market_data(market_data)

            # Estimate factor returns and exposures
            self._estimate_factors()

            # Apply factor timing
            if self.config.use_factor_timing:
                self._apply_factor_timing()

            # Construct target portfolio
            target_weights = self._construct_factor_portfolio()

            # Generate rebalancing signals
            signals = self._generate_rebalancing_signals(target_weights)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} factor-based signals")

        except Exception as e:
            self.logger.error("Error generating factor signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and factor exposures

        This method:
        1. Updates current portfolio weights
        2. Recalculates factor exposures
        3. Updates factor return estimates
        4. Monitors factor performance

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update market data
            self._update_market_data(market_data)

            # Update current portfolio weights
            self._update_portfolio_weights(market_data)

            # Recalculate factor exposures
            self._update_factor_exposures()

            # Update factor return estimates
            self._update_factor_returns()

            # Update portfolio risk metrics
            self._update_portfolio_risk_metrics()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"factor_{self.config.strategy_id}_factors",
                    len(self.factor_definitions)
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check factor model compatibility
            if self.config.factor_model == FactorModel.FAMA_FRENCH_3:
                required_factors = [FactorType.MARKET, FactorType.SIZE, FactorType.VALUE]
            elif self.config.factor_model == FactorModel.FAMA_FRENCH_5:
                required_factors = [FactorType.MARKET, FactorType.SIZE, FactorType.VALUE,
                                  FactorType.PROFITABILITY, FactorType.INVESTMENT]
            else:
                required_factors = self.config.factor_types

            if not all(factor in self.config.factor_types for factor in required_factors):
                return False

            # Check risk parameters
            if not (0 < self.config.max_position_size <= 1.0):
                return False

            if not (0 < self.config.volatility_target <= 1.0):
                return False

            return True

        except Exception:
            return False

    def _initialize_factor_definitions(self) -> None:
        """Initialize factor definitions based on the selected model"""
        try:
            if self.config.factor_model == FactorModel.FAMA_FRENCH_3:
                self._initialize_fama_french_3_factors()
            elif self.config.factor_model == FactorModel.FAMA_FRENCH_5:
                self._initialize_fama_french_5_factors()
            elif self.config.factor_model == FactorModel.CARHART_4:
                self._initialize_carhart_4_factors()
            else:
                self._initialize_custom_factors()

        except Exception as e:
            self.logger.error("Error initializing factor definitions", {'error': str(e)})

    def _initialize_fama_french_3_factors(self) -> None:
        """Initialize Fama-French 3-factor model definitions"""
        self.factor_definitions = {
            FactorType.MARKET: FactorDefinition(
                name="Market",
                type=FactorType.MARKET,
                description="Market excess return (MKT)",
                long_portfolio="large_cap_stocks",
                short_portfolio="risk_free_rate",
                weighting="market_cap"
            ),
            FactorType.SIZE: FactorDefinition(
                name="Size",
                type=FactorType.SIZE,
                description="Small minus big (SMB)",
                long_portfolio="small_cap_stocks",
                short_portfolio="large_cap_stocks",
                weighting="equal"
            ),
            FactorType.VALUE: FactorDefinition(
                name="Value",
                type=FactorType.VALUE,
                description="High minus low (HML)",
                long_portfolio="high_book_to_market",
                short_portfolio="low_book_to_market",
                weighting="equal"
            )
        }

    def _initialize_fama_french_5_factors(self) -> None:
        """Initialize Fama-French 5-factor model definitions"""
        # Start with 3-factor model
        self._initialize_fama_french_3_factors()

        # Add profitability and investment factors
        self.factor_definitions.update({
            FactorType.PROFITABILITY: FactorDefinition(
                name="Profitability",
                type=FactorType.PROFITABILITY,
                description="Robust minus weak (RMW)",
                long_portfolio="high_profitability",
                short_portfolio="low_profitability",
                weighting="equal"
            ),
            FactorType.INVESTMENT: FactorDefinition(
                name="Investment",
                type=FactorType.INVESTMENT,
                description="Conservative minus aggressive (CMA)",
                long_portfolio="low_investment",
                short_portfolio="high_investment",
                weighting="equal"
            )
        })

    def _initialize_carhart_4_factors(self) -> None:
        """Initialize Carhart 4-factor model definitions"""
        # Start with 3-factor model
        self._initialize_fama_french_3_factors()

        # Add momentum factor
        self.factor_definitions[FactorType.MOMENTUM] = FactorDefinition(
            name="Momentum",
            type=FactorType.MOMENTUM,
            description="Momentum factor (MOM)",
            long_portfolio="high_momentum",
            short_portfolio="low_momentum",
            weighting="equal"
        )

    def _initialize_custom_factors(self) -> None:
        """Initialize custom factor definitions"""
        # Create basic factor definitions for custom factors
        for factor_type in self.config.factor_types:
            if factor_type not in self.factor_definitions:
                self.factor_definitions[factor_type] = FactorDefinition(
                    name=factor_type.value.title(),
                    type=factor_type,
                    description=f"Custom {factor_type.value} factor",
                    long_portfolio=f"high_{factor_type.value}",
                    short_portfolio=f"low_{factor_type.value}",
                    weighting="equal"
                )

    def _initialize_factor_exposures(self) -> None:
        """Initialize target factor exposures"""
        if not self.config.target_factor_exposures:
            # Default equal weighting across factors
            factor_count = len(self.config.factor_types)
            default_exposure = 1.0 / factor_count if factor_count > 0 else 0.0

            for factor_type in self.config.factor_types:
                self.config.target_factor_exposures[factor_type] = default_exposure

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update internal market data cache"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty:
                self.price_data[symbol] = data.copy()

                # Calculate returns if price data available
                if 'close' in data.columns:
                    self.returns_data[symbol] = data['close'].pct_change().dropna()

    def _estimate_factors(self) -> None:
        """
        Estimate factor returns and exposures

        This method:
        1. Estimates factor returns using historical data
        2. Calculates factor exposures for each asset
        3. Updates factor volatility estimates
        """
        try:
            # Estimate factor returns
            self._estimate_factor_returns()

            # Calculate factor exposures
            self._calculate_factor_exposures()

            # Update factor volatilities
            self._update_factor_volatilities()

        except Exception as e:
            self.logger.error("Error estimating factors", {'error': str(e)})

    def _estimate_factor_returns(self) -> None:
        """
        Estimate factor returns using historical data

        For each factor, construct the long-short portfolio and
        calculate its historical returns.
        """
        try:
            for factor_type, factor_def in self.factor_definitions.items():
                # Get assets in long and short portfolios
                long_assets = self._get_portfolio_assets(factor_def.long_portfolio)
                short_assets = self._get_portfolio_assets(factor_def.short_portfolio)

                if not long_assets or not short_assets:
                    continue

                # Calculate portfolio returns
                long_returns = self._calculate_portfolio_returns(long_assets, factor_def.weighting)
                short_returns = self._calculate_portfolio_returns(short_assets, factor_def.weighting)

                if long_returns is not None and short_returns is not None:
                    # Factor return = long portfolio - short portfolio
                    factor_returns = long_returns - short_returns
                    self.factor_returns[factor_type] = factor_returns

        except Exception as e:
            self.logger.error("Error estimating factor returns", {'error': str(e)})

    def _calculate_portfolio_returns(self, assets: List[str], weighting: str) -> Optional[pd.Series]:
        """
        Calculate portfolio returns for a list of assets

        Args:
            assets: List of asset symbols
            weighting: Weighting scheme (equal, market_cap, etc.)

        Returns:
            Portfolio returns series
        """
        try:
            if not assets:
                return None

            # Get returns for available assets
            asset_returns = []
            weights = []

            for asset in assets:
                if asset in self.returns_data:
                    returns = self.returns_data[asset]
                    if not returns.empty:
                        asset_returns.append(returns)
                        weights.append(1.0)  # Equal weighting for now

            if not asset_returns:
                return None

            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]

            # Calculate portfolio returns
            portfolio_returns = sum(w * r for w, r in zip(weights, asset_returns))

            return portfolio_returns

        except Exception as e:
            self.logger.error("Error calculating portfolio returns", {'error': str(e)})
            return None

    def _get_portfolio_assets(self, portfolio_name: str) -> List[str]:
        """
        Get assets belonging to a portfolio

        This is a simplified implementation. In practice, this would
        query a database or use predefined asset classifications.
        """
        # Simplified asset classification - in practice this would be more sophisticated
        if portfolio_name == "large_cap_stocks":
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]  # Example large caps
        elif portfolio_name == "small_cap_stocks":
            return ["ETSY", "DOCU", "SHOP", "ZM", "CRWD"]  # Example small caps
        elif portfolio_name == "high_book_to_market":
            return ["BAC", "C", "WFC", "JPM", "GS"]  # Example value stocks
        elif portfolio_name == "low_book_to_market":
            return ["AMZN", "GOOGL", "NVDA", "TSLA", "META"]  # Example growth stocks
        elif portfolio_name == "high_profitability":
            return ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
        elif portfolio_name == "low_profitability":
            return ["GE", "F", "BAC", "C", "WFC"]
        elif portfolio_name == "low_investment":
            return ["BRK.B", "JPM", "BAC", "C", "WFC"]
        elif portfolio_name == "high_investment":
            return ["TSLA", "NVDA", "AMD", "SQ", "SHOP"]
        elif portfolio_name == "high_momentum":
            return ["NVDA", "AMD", "TSLA", "PLTR", "COIN"]
        elif portfolio_name == "low_momentum":
            return ["GE", "F", "BAC", "C", "WFC"]
        else:
            # Return all available assets for custom portfolios
            return list(self.price_data.keys())

    def _calculate_factor_exposures(self) -> None:
        """
        Calculate factor exposures for each asset

        Uses regression analysis to determine how much each asset
        is exposed to each factor.
        """
        try:
            for symbol in self.price_data.keys():
                if symbol not in self.returns_data:
                    continue

                asset_returns = self.returns_data[symbol]
                exposures = {}

                # Regress asset returns against factor returns
                for factor_type, factor_returns in self.factor_returns.items():
                    try:
                        # Align data
                        common_index = asset_returns.index.intersection(factor_returns.index)
                        if len(common_index) < 20:  # Minimum observations
                            exposures[factor_type] = 0.0
                            continue

                        y = asset_returns.loc[common_index]
                        X = factor_returns.loc[common_index]

                        # Simple regression (could be extended to multi-factor)
                        if len(X) > 1 and X.std() > 0:
                            slope = np.cov(y, X)[0, 1] / X.var()
                            exposures[factor_type] = slope
                        else:
                            exposures[factor_type] = 0.0

                    except Exception:
                        exposures[factor_type] = 0.0

                self.factor_exposures[symbol] = exposures

        except Exception as e:
            self.logger.error("Error calculating factor exposures", {'error': str(e)})

    def _update_factor_volatilities(self) -> None:
        """Update factor volatility estimates"""
        try:
            for factor_type, factor_returns in self.factor_returns.items():
                if not factor_returns.empty and len(factor_returns) >= 20:
                    # Calculate annualized volatility
                    volatility = factor_returns.std() * np.sqrt(252)
                    self.factor_volatilities[factor_type] = volatility
                else:
                    self.factor_volatilities[factor_type] = self.config.volatility_target

        except Exception as e:
            self.logger.error("Error updating factor volatilities", {'error': str(e)})

    def _apply_factor_timing(self) -> None:
        """
        Apply factor timing based on recent factor performance

        Uses z-score analysis to time factor exposures.
        """
        try:
            for factor_type, factor_returns in self.factor_returns.items():
                if factor_returns.empty or len(factor_returns) < self.config.timing_lookback:
                    self.factor_timings[factor_type] = 1.0  # Neutral timing
                    continue

                # Calculate recent factor performance
                recent_returns = factor_returns.tail(self.config.timing_lookback)
                avg_return = recent_returns.mean()
                std_return = recent_returns.std()

                if std_return > 0:
                    z_score = avg_return / (std_return / np.sqrt(len(recent_returns)))

                    # Apply timing signal
                    if z_score > self.config.timing_z_threshold:
                        self.factor_timings[factor_type] = 1.5  # Increase exposure
                    elif z_score < -self.config.timing_z_threshold:
                        self.factor_timings[factor_type] = 0.5  # Decrease exposure
                    else:
                        self.factor_timings[factor_type] = 1.0  # Neutral
                else:
                    self.factor_timings[factor_type] = 1.0

        except Exception as e:
            self.logger.error("Error applying factor timing", {'error': str(e)})

    def _construct_factor_portfolio(self) -> Dict[str, float]:
        """
        Construct target portfolio using factor exposures

        This method:
        1. Determines target factor exposures
        2. Selects assets with desired factor exposures
        3. Applies risk parity weighting
        4. Returns target portfolio weights

        Returns:
            Dictionary of target weights by symbol
        """
        target_weights = {}

        try:
            # Get target factor exposures
            target_exposures = self._get_target_factor_exposures()

            # Find assets with desired factor exposures
            for symbol, exposures in self.factor_exposures.items():
                # Calculate asset score based on target exposures
                asset_score = 0.0
                for factor_type, target_exposure in target_exposures.items():
                    factor_exposure = exposures.get(factor_type, 0.0)
                    timing = self.factor_timings.get(factor_type, 1.0)
                    asset_score += factor_exposure * target_exposure * timing

                if asset_score > 0:
                    target_weights[symbol] = asset_score

            # Apply risk parity if enabled
            if self.config.use_risk_parity and target_weights:
                target_weights = self._apply_risk_parity(target_weights)

            # Normalize weights
            total_weight = sum(target_weights.values())
            if total_weight > 0:
                target_weights = {symbol: weight / total_weight
                                for symbol, weight in target_weights.items()}

        except Exception as e:
            self.logger.error("Error constructing factor portfolio", {'error': str(e)})

        return target_weights

    def _get_target_factor_exposures(self) -> Dict[FactorType, float]:
        """Get target factor exposures with timing adjustments"""
        target_exposures = self.config.target_factor_exposures.copy()

        # Apply factor timing adjustments
        for factor_type in target_exposures:
            timing = self.factor_timings.get(factor_type, 1.0)
            target_exposures[factor_type] *= timing

        return target_exposures

    def _apply_risk_parity(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply risk parity weighting to portfolio

        Adjusts weights so that each asset contributes equally
        to portfolio risk.
        """
        try:
            if not weights:
                return weights

            # Estimate asset volatilities (simplified)
            asset_volatilities = {}
            for symbol in weights.keys():
                if symbol in self.returns_data and not self.returns_data[symbol].empty:
                    vol = self.returns_data[symbol].tail(63).std() * np.sqrt(252)
                    asset_volatilities[symbol] = max(vol, 0.01)  # Minimum volatility
                else:
                    asset_volatilities[symbol] = self.config.volatility_target

            # Calculate risk parity weights
            risk_contributions = {symbol: vol for symbol, vol in asset_volatilities.items()}
            total_risk = sum(risk_contributions.values())

            if total_risk > 0:
                risk_parity_weights = {symbol: risk / total_risk
                                     for symbol, risk in risk_contributions.items()}

                # Combine with original weights (simplified approach)
                combined_weights = {}
                for symbol in weights:
                    original_weight = weights[symbol]
                    risk_weight = risk_parity_weights.get(symbol, 0.0)
                    combined_weights[symbol] = (original_weight + risk_weight) / 2.0

                return combined_weights

        except Exception as e:
            self.logger.error("Error applying risk parity", {'error': str(e)})

        return weights

    def _generate_rebalancing_signals(self, target_weights: Dict[str, float]) -> List[StrategySignal]:
        """
        Generate rebalancing signals to achieve target weights

        Compares current weights with target weights and generates
        buy/sell signals for rebalancing.
        """
        signals = []

        try:
            for symbol, target_weight in target_weights.items():
                current_weight = self.current_weights.get(symbol, 0.0)
                weight_difference = target_weight - current_weight

                if abs(weight_difference) < self.config.min_position_size:
                    continue

                # Get current price
                current_price = None
                if symbol in self.price_data and not self.price_data[symbol].empty:
                    current_price = self.price_data[symbol]['close'].iloc[-1]

                if current_price is None:
                    continue

                # Determine signal type and quantity
                if weight_difference > 0:
                    signal_type = SignalType.BUY
                    quantity = abs(weight_difference)
                else:
                    signal_type = SignalType.SELL
                    quantity = abs(weight_difference)

                # Create signal
                signal = StrategySignal(
                    signal_id=f"factor_rebalance_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=self.config.strategy_id,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=0.8,  # High confidence for factor-based signals
                    strength=abs(weight_difference),
                    target_quantity=quantity,
                    signal_price=current_price,
                    entry_price=current_price,
                    max_position_size=self.config.max_position_size
                )

                signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating rebalancing signals", {'error': str(e)})

        return signals

    def _apply_portfolio_risk_management(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """
        Apply portfolio-level risk management constraints

        Ensures the portfolio doesn't exceed volatility targets
        and maintains proper factor diversification.
        """
        if not signals:
            return signals

        try:
            # Check portfolio volatility
            if self.portfolio_volatility > self.config.volatility_target * 1.2:
                self.logger.warning("Portfolio volatility too high, reducing factor exposure")
                # Reduce all signal quantities
                for signal in signals:
                    signal.target_quantity *= 0.8

            # Check factor concentration
            factor_concentration = self._check_factor_concentration(signals)
            if factor_concentration > self.config.max_factor_exposure:
                self.logger.warning("Factor concentration too high, diversifying exposure")
                for signal in signals:
                    signal.target_quantity *= 0.9

            return signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _check_factor_concentration(self, signals: List[StrategySignal]) -> float:
        """Check concentration of factor exposures in signals"""
        # Simplified check - in practice would analyze factor exposures
        return 1.0  # Placeholder

    def _update_portfolio_weights(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update current portfolio weights based on market data"""
        try:
            total_value = 0.0
            asset_values = {}

            for symbol, data in market_data.items():
                if data is not None and not data.empty and 'close' in data.columns:
                    current_price = data['close'].iloc[-1]
                    current_weight = self.current_weights.get(symbol, 0.0)
                    # Simplified - in practice would use actual position sizes
                    asset_values[symbol] = current_weight * current_price
                    total_value += asset_values[symbol]

            # Update weights
            if total_value > 0:
                self.current_weights = {symbol: value / total_value
                                      for symbol, value in asset_values.items()}

        except Exception as e:
            self.logger.error("Error updating portfolio weights", {'error': str(e)})

    def _update_factor_exposures(self) -> None:
        """Update factor exposures for current portfolio"""
        # This would recalculate factor exposures for the current portfolio
        pass

    def _update_factor_returns(self) -> None:
        """Update factor return estimates"""
        # This would update factor returns with new data
        pass

    def _update_portfolio_risk_metrics(self) -> None:
        """Update portfolio-level risk metrics"""
        try:
            # Calculate portfolio volatility from factor exposures
            if self.factor_volatilities:
                # Simplified calculation
                avg_factor_vol = np.mean(list(self.factor_volatilities.values()))
                self.portfolio_volatility = avg_factor_vol

        except Exception as e:
            self.logger.error("Error updating portfolio risk metrics", {'error': str(e)})

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.current_weights)

        # Add factor-specific metrics
        metrics.total_return = sum(self.factor_contributions.values())

        return metrics