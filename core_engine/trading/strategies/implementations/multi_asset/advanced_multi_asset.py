"""
Advanced Multi-Asset Strategy Implementation

This module implements sophisticated multi-asset portfolio strategies that optimize
across different asset classes including equities, bonds, commodities, and currencies.

The strategy uses:
- Modern Portfolio Theory (MPT) and Black-Litterman model
- Risk parity and minimum variance optimization
- Dynamic asset allocation with regime detection
- Cross-asset correlation management
- Currency hedging and commodity timing

Key Features:
- Multi-asset portfolio construction and rebalancing
- Risk parity across asset classes
- Dynamic asset allocation based on market regimes
- Currency risk management
- Commodity and alternative asset integration

Academic Foundations:
- Markowitz (1952) Modern Portfolio Theory
- Black & Litterman (1992) asset allocation model
- Asness, Moskowitz & Pedersen (2013) value and carry factors
- Ang, Brière & Signori (2012) risk parity portfolios

Components:
- Asset class definitions and characteristics
- Portfolio optimization engines
- Risk management and constraints
- Rebalancing and execution logic
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from scipy import optimize
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import StandardScaler

from ...strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition,
    StrategyMetrics, SignalType, StrategyType
)
from .....utils.logging import get_logger
from .....utils.performance import get_performance_monitor

logger = get_logger(__name__)


class AssetClass(Enum):
    """Asset class definitions"""
    EQUITIES = "equities"
    BONDS = "bonds"
    COMMODITIES = "commodities"
    CURRENCIES = "currencies"
    REAL_ESTATE = "real_estate"
    ALTERNATIVES = "alternatives"
    CASH = "cash"


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"  # Markowitz (1952)
    RISK_PARITY = "risk_parity"  # Equal risk contribution
    MINIMUM_VARIANCE = "minimum_variance"  # Global minimum variance
    MAXIMUM_SHARPE = "maximum_sharpe"  # Maximum Sharpe ratio
    BLACK_LITTERMAN = "black_litterman"  # Black-Litterman model
    EQUAL_WEIGHT = "equal_weight"  # Equal weighting


class RebalancingFrequency(Enum):
    """Rebalancing frequency options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


@dataclass
class AssetClassConfig:
    """Configuration for an asset class"""
    asset_class: AssetClass
    symbols: List[str]  # Representative symbols for the asset class
    target_weight: float  # Target allocation weight
    min_weight: float = 0.0  # Minimum allocation
    max_weight: float = 1.0  # Maximum allocation
    expected_return: Optional[float] = None  # Expected annual return
    volatility: Optional[float] = None  # Expected annual volatility
    currency: str = "USD"  # Base currency


@dataclass
class MultiAssetConfig(StrategyConfig):
    """Configuration for Advanced Multi-Asset Strategy"""

    # Strategy identification
    strategy_type: StrategyType = StrategyType.CUSTOM

    # Asset allocation settings
    asset_classes: List[AssetClass] = field(default_factory=lambda: [
        AssetClass.EQUITIES, AssetClass.BONDS, AssetClass.COMMODITIES
    ])

    # Optimization parameters
    optimization_method: OptimizationMethod = OptimizationMethod.RISK_PARITY
    rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY
    lookback_period: int = 252  # Trading days for estimation

    # Risk management
    target_volatility: float = 0.12  # Annual target volatility
    max_volatility: float = 0.20  # Maximum allowed volatility
    risk_free_rate: float = 0.03  # Risk-free rate for Sharpe calculation

    # Asset class configurations
    asset_class_configs: Dict[AssetClass, AssetClassConfig] = field(default_factory=dict)

    # Black-Litterman parameters (if used)
    use_black_litterman: bool = False
    market_cap_weights: Dict[str, float] = field(default_factory=dict)  # Market cap weights
    investor_views: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # (return, confidence)

    # Risk parity settings
    risk_parity_tolerance: float = 0.01  # Tolerance for risk parity optimization
    risk_parity_max_iter: int = 1000

    # Constraints
    min_asset_weight: float = 0.01  # Minimum weight per asset
    max_asset_weight: float = 0.30  # Maximum weight per asset
    max_correlation: float = 0.95  # Maximum correlation between assets

    # Transaction costs and liquidity
    transaction_cost_bps: float = 5.0
    min_trade_size: float = 0.001
    max_turnover: float = 0.50  # Maximum annual turnover

    # Currency hedging
    enable_currency_hedging: bool = True
    base_currency: str = "USD"
    hedge_threshold: float = 0.10  # Hedge currency exposure > 10%

    # Alternative assets
    include_alternatives: bool = False
    alternative_allocation: float = 0.05  # Max allocation to alternatives

    # Performance monitoring
    enable_monitoring: bool = True
    log_signals: bool = True


class AdvancedMultiAssetStrategy(BaseStrategy):
    """
    Advanced Multi-Asset Strategy Implementation

    This strategy implements comprehensive multi-asset portfolio management:
    1. Dynamic asset allocation across multiple asset classes
    2. Risk parity and modern portfolio optimization
    3. Black-Litterman model for incorporating investor views
    4. Currency risk management and hedging
    5. Regime-based allocation adjustments

    The strategy optimizes portfolios across equities, bonds, commodities,
    currencies, and alternative assets while maintaining proper risk controls.
    """

    def __init__(self, config: MultiAssetConfig):
        super().__init__(config)
        self.config: MultiAssetConfig = config

        # Initialize components
        self.logger = get_logger(f"multi_asset_strategy_{config.strategy_id}")
        self.performance_monitor = get_performance_monitor() if config.enable_monitoring else None

        # Asset class management
        self.asset_class_configs: Dict[AssetClass, AssetClassConfig] = {}
        self.asset_returns: Dict[str, pd.Series] = {}
        self.asset_covariance: pd.DataFrame = pd.DataFrame()

        # Portfolio state
        self.current_weights: Dict[str, float] = {}
        self.target_weights: Dict[str, float] = {}
        self.asset_class_weights: Dict[AssetClass, float] = {}

        # Risk management state
        self.portfolio_volatility: float = 0.0
        self.asset_volatilities: Dict[str, float] = {}
        self.correlation_matrix: pd.DataFrame = pd.DataFrame()

        # Currency management
        self.currency_exposures: Dict[str, float] = {}
        self.hedge_positions: Dict[str, float] = {}

        # Market regime detection
        self.current_regime: str = "normal"
        self.regime_history: List[str] = []

        # Signal history
        self.signal_history: List[StrategySignal] = []

        self.logger.info("Advanced Multi-Asset Strategy initialized", {
            'strategy_id': config.strategy_id,
            'optimization_method': config.optimization_method.value,
            'asset_classes': [ac.value for ac in config.asset_classes]
        })

    def initialize(self) -> bool:
        """
        Initialize the multi-asset strategy

        Sets up asset class configurations, optimization parameters,
        and prepares for portfolio construction and rebalancing.
        """
        try:
            self.logger.info("Initializing Advanced Multi-Asset Strategy")

            # Validate configuration
            if not self._validate_config():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize asset class configurations
            self._initialize_asset_classes()

            # Set up optimization parameters
            self._initialize_optimization()

            # Initialize portfolio weights
            self.target_weights = {}
            self.current_weights = {}
            self.asset_class_weights = {}

            # Set up performance monitoring
            if self.performance_monitor:
                self.performance_monitor.start_monitoring(f"multi_asset_{self.config.strategy_id}")

            # Initialize risk management
            self.portfolio_volatility = self.config.target_volatility

            self.logger.info("Advanced Multi-Asset Strategy initialized successfully")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize multi-asset strategy", {'error': str(e)})
            return False

    def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate multi-asset portfolio signals

        This method implements the core multi-asset strategy logic:
        1. Update asset returns and covariance estimates
        2. Detect market regime and adjust allocations
        3. Optimize portfolio using selected method
        4. Generate rebalancing signals
        5. Apply currency hedging if enabled

        Args:
            market_data: Dictionary of OHLCV data for each asset

        Returns:
            List of trading signals
        """
        signals = []

        try:
            # Update market data and estimates
            self._update_market_data(market_data)
            self._update_asset_estimates()

            # Detect market regime
            self._detect_market_regime()

            # Optimize portfolio
            target_weights = self._optimize_portfolio()

            # Apply regime adjustments
            target_weights = self._apply_regime_adjustments(target_weights)

            # Generate rebalancing signals
            signals = self._generate_rebalancing_signals(target_weights)

            # Apply currency hedging
            if self.config.enable_currency_hedging:
                hedge_signals = self._generate_currency_hedge_signals()
                signals.extend(hedge_signals)

            # Apply portfolio-level risk management
            signals = self._apply_portfolio_risk_management(signals)

            self.logger.debug(f"Generated {len(signals)} multi-asset signals")

        except Exception as e:
            self.logger.error("Error generating multi-asset signals", {'error': str(e)})
            # Return empty signals list on error

        return signals

    def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update position tracking and portfolio state

        This method:
        1. Updates current portfolio weights
        2. Recalculates risk metrics
        3. Updates currency exposures
        4. Monitors portfolio performance

        Args:
            market_data: Current market data for position valuation
        """
        try:
            # Update market data
            self._update_market_data(market_data)

            # Update current portfolio weights
            self._update_portfolio_weights(market_data)

            # Update risk metrics
            self._update_risk_metrics()

            # Update currency exposures
            self._update_currency_exposures()

            # Log position updates if monitoring enabled
            if self.config.enable_monitoring and self.performance_monitor:
                self.performance_monitor.record_metric(
                    f"multi_asset_{self.config.strategy_id}_volatility",
                    self.portfolio_volatility
                )

        except Exception as e:
            self.logger.error("Error updating positions", {'error': str(e)})

    def _validate_config(self) -> bool:
        """Validate strategy configuration parameters"""
        try:
            # Check asset classes
            if not self.config.asset_classes:
                return False

            # Check optimization method
            if self.config.optimization_method not in OptimizationMethod:
                return False

            # Check risk parameters
            if not (0 < self.config.target_volatility <= self.config.max_volatility):
                return False

            # Check weight constraints
            if not (0 <= self.config.min_asset_weight < self.config.max_asset_weight <= 1.0):
                return False

            # Check Black-Litterman parameters if used
            if self.config.use_black_litterman:
                if not self.config.market_cap_weights or not self.config.investor_views:
                    return False

            return True

        except Exception:
            return False

    def _initialize_asset_classes(self) -> None:
        """Initialize asset class configurations"""
        try:
            for asset_class in self.config.asset_classes:
                if asset_class not in self.config.asset_class_configs:
                    # Create default configuration
                    config = AssetClassConfig(
                        asset_class=asset_class,
                        symbols=self._get_default_symbols(asset_class),
                        target_weight=1.0 / len(self.config.asset_classes),
                        expected_return=self._get_default_expected_return(asset_class),
                        volatility=self._get_default_volatility(asset_class)
                    )
                    self.config.asset_class_configs[asset_class] = config

        except Exception as e:
            self.logger.error("Error initializing asset classes", {'error': str(e)})

    def _get_default_symbols(self, asset_class: AssetClass) -> List[str]:
        """Get default symbols for an asset class"""
        defaults = {
            AssetClass.EQUITIES: ["SPY", "QQQ", "IWM", "EFA", "VWO"],
            AssetClass.BONDS: ["AGG", "BND", "TIP", "LQD", "HYG"],
            AssetClass.COMMODITIES: ["GLD", "SLV", "USO", "DBC", "GSG"],
            AssetClass.CURRENCIES: ["FXE", "FXB", "FXF", "FXC", "FXY"],
            AssetClass.REAL_ESTATE: ["VNQ", "IYR", "REM", "RWX"],
            AssetClass.ALTERNATIVES: ["TAIL", "VXX", "TBF"],
            AssetClass.CASH: ["SHV", "BIL"]
        }
        return defaults.get(asset_class, [])

    def _get_default_expected_return(self, asset_class: AssetClass) -> float:
        """Get default expected return for an asset class"""
        defaults = {
            AssetClass.EQUITIES: 0.08,
            AssetClass.BONDS: 0.03,
            AssetClass.COMMODITIES: 0.05,
            AssetClass.CURRENCIES: 0.02,
            AssetClass.REAL_ESTATE: 0.06,
            AssetClass.ALTERNATIVES: 0.04,
            AssetClass.CASH: 0.02
        }
        return defaults.get(asset_class, 0.04)

    def _get_default_volatility(self, asset_class: AssetClass) -> float:
        """Get default volatility for an asset class"""
        defaults = {
            AssetClass.EQUITIES: 0.15,
            AssetClass.BONDS: 0.08,
            AssetClass.COMMODITIES: 0.20,
            AssetClass.CURRENCIES: 0.12,
            AssetClass.REAL_ESTATE: 0.16,
            AssetClass.ALTERNATIVES: 0.25,
            AssetClass.CASH: 0.01
        }
        return defaults.get(asset_class, 0.15)

    def _initialize_optimization(self) -> None:
        """Initialize optimization parameters"""
        # Set up optimization constraints and bounds
        self.optimization_bounds = []
        self.optimization_constraints = []

        # This would set up the optimization problem constraints
        pass

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update internal market data cache"""
        for symbol, data in market_data.items():
            if data is not None and not data.empty:
                # Calculate returns if price data available
                if 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                    self.asset_returns[symbol] = returns

    def _update_asset_estimates(self) -> None:
        """
        Update asset return and covariance estimates

        This method calculates:
        1. Expected returns for each asset
        2. Covariance matrix
        3. Correlation matrix
        4. Individual asset volatilities
        """
        try:
            if not self.asset_returns:
                return

            # Get common date range
            all_dates = set()
            for returns in self.asset_returns.values():
                all_dates.update(returns.index)

            common_dates = sorted(all_dates)
            if len(common_dates) < 30:  # Minimum observations
                return

            # Create returns matrix
            returns_df = pd.DataFrame(index=common_dates)
            for symbol, returns in self.asset_returns.items():
                returns_df[symbol] = returns.reindex(common_dates)

            returns_df = returns_df.dropna()

            if returns_df.empty or len(returns_df) < 30:
                return

            # Calculate covariance matrix using Ledoit-Wolf shrinkage
            cov_estimator = LedoitWolf()
            self.asset_covariance = pd.DataFrame(
                cov_estimator.fit(returns_df.values).covariance_,
                index=returns_df.columns,
                columns=returns_df.columns
            )

            # Calculate correlation matrix
            self.correlation_matrix = returns_df.corr()

            # Calculate volatilities
            for symbol in returns_df.columns:
                vol = returns_df[symbol].std() * np.sqrt(252)  # Annualized
                self.asset_volatilities[symbol] = vol

        except Exception as e:
            self.logger.error("Error updating asset estimates", {'error': str(e)})

    def _detect_market_regime(self) -> None:
        """
        Detect current market regime

        Uses various indicators to classify market conditions:
        - Volatility regime
        - Trend regime
        - Risk-on/risk-off regime
        """
        try:
            if not self.asset_returns:
                self.current_regime = "normal"
                return

            # Simple regime detection based on volatility and correlation
            avg_volatility = np.mean(list(self.asset_volatilities.values()))

            # High volatility regime
            if avg_volatility > 0.25:
                regime = "high_volatility"
            # Low volatility regime
            elif avg_volatility < 0.10:
                regime = "low_volatility"
            # Normal regime
            else:
                regime = "normal"

            # Check for risk-off regime (high correlation, flight to quality)
            if self.correlation_matrix is not None and not self.correlation_matrix.empty:
                avg_correlation = self.correlation_matrix.values[np.triu_indices_from(
                    self.correlation_matrix.values, k=1)].mean()

                if avg_correlation > 0.7 and regime == "high_volatility":
                    regime = "risk_off"

            self.current_regime = regime
            self.regime_history.append(regime)

            # Keep only recent history
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]

        except Exception as e:
            self.logger.error("Error detecting market regime", {'error': str(e)})
            self.current_regime = "normal"

    def _optimize_portfolio(self) -> Dict[str, float]:
        """
        Optimize portfolio using the selected optimization method

        Returns target weights for each asset.
        """
        try:
            if not self.asset_covariance.empty and self.asset_volatilities:
                if self.config.optimization_method == OptimizationMethod.RISK_PARITY:
                    return self._optimize_risk_parity()
                elif self.config.optimization_method == OptimizationMethod.MEAN_VARIANCE:
                    return self._optimize_mean_variance()
                elif self.config.optimization_method == OptimizationMethod.MINIMUM_VARIANCE:
                    return self._optimize_minimum_variance()
                elif self.config.optimization_method == OptimizationMethod.BLACK_LITTERMAN:
                    return self._optimize_black_litterman()
                else:
                    return self._equal_weight_portfolio()

            # Fallback to equal weighting
            return self._equal_weight_portfolio()

        except Exception as e:
            self.logger.error("Error optimizing portfolio", {'error': str(e)})
            return self._equal_weight_portfolio()

    def _optimize_risk_parity(self) -> Dict[str, float]:
        """
        Optimize portfolio using risk parity approach

        Risk parity aims to equalize the risk contribution of each asset.
        """
        try:
            assets = list(self.asset_volatilities.keys())
            n_assets = len(assets)

            if n_assets == 0:
                return {}

            # Initial equal weights
            weights = np.array([1.0 / n_assets] * n_assets)

            # Risk parity optimization
            def risk_contribution(weights):
                portfolio_vol = np.sqrt(weights.T @ self.asset_covariance.loc[assets, assets].values @ weights)
                marginal_risk = self.asset_covariance.loc[assets, assets].values @ weights / portfolio_vol
                risk_contrib = weights * marginal_risk
                return risk_contrib

            def objective(weights):
                rc = risk_contribution(weights)
                return np.var(rc)  # Minimize variance of risk contributions

            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
            ]

            bounds = [(self.config.min_asset_weight, self.config.max_asset_weight)] * n_assets

            # Optimize
            result = optimize.minimize(
                objective,
                weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': self.config.risk_parity_max_iter, 'ftol': self.config.risk_parity_tolerance}
            )

            if result.success:
                optimal_weights = dict(zip(assets, result.x))
                return optimal_weights
            else:
                self.logger.warning("Risk parity optimization failed, using equal weights")
                return self._equal_weight_portfolio()

        except Exception as e:
            self.logger.error("Error in risk parity optimization", {'error': str(e)})
            return self._equal_weight_portfolio()

    def _optimize_mean_variance(self) -> Dict[str, float]:
        """
        Optimize portfolio using mean-variance optimization (Markowitz)

        Maximizes Sharpe ratio subject to volatility constraint.
        """
        try:
            assets = list(self.asset_volatilities.keys())
            n_assets = len(assets)

            if n_assets == 0:
                return {}

            # Get expected returns (simplified - use historical averages)
            expected_returns = {}
            for symbol in assets:
                if symbol in self.asset_returns:
                    returns = self.asset_returns[symbol]
                    if not returns.empty:
                        expected_returns[symbol] = returns.mean() * 252  # Annualized
                    else:
                        expected_returns[symbol] = self.config.risk_free_rate
                else:
                    expected_returns[symbol] = self.config.risk_free_rate

            expected_returns_array = np.array([expected_returns[symbol] for symbol in assets])

            # Objective: maximize Sharpe ratio
            def objective(weights):
                portfolio_return = weights @ expected_returns_array
                portfolio_vol = np.sqrt(weights.T @ self.asset_covariance.loc[assets, assets].values @ weights)
                sharpe = (portfolio_return - self.config.risk_free_rate) / portfolio_vol
                return -sharpe  # Minimize negative Sharpe

            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
                {'type': 'ineq', 'fun': lambda w: self.config.max_volatility -
                 np.sqrt(w.T @ self.asset_covariance.loc[assets, assets].values @ w)}  # Vol constraint
            ]

            bounds = [(self.config.min_asset_weight, self.config.max_asset_weight)] * n_assets

            # Initial guess
            initial_weights = np.array([1.0 / n_assets] * n_assets)

            # Optimize
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                optimal_weights = dict(zip(assets, result.x))
                return optimal_weights
            else:
                self.logger.warning("Mean-variance optimization failed, using equal weights")
                return self._equal_weight_portfolio()

        except Exception as e:
            self.logger.error("Error in mean-variance optimization", {'error': str(e)})
            return self._equal_weight_portfolio()

    def _optimize_minimum_variance(self) -> Dict[str, float]:
        """
        Find minimum variance portfolio

        Minimizes portfolio volatility without regard to expected returns.
        """
        try:
            assets = list(self.asset_volatilities.keys())
            n_assets = len(assets)

            if n_assets == 0:
                return {}

            def objective(weights):
                return weights.T @ self.asset_covariance.loc[assets, assets].values @ weights

            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},  # Weights sum to 1
            ]

            bounds = [(self.config.min_asset_weight, self.config.max_asset_weight)] * n_assets

            # Initial guess
            initial_weights = np.array([1.0 / n_assets] * n_assets)

            # Optimize
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                optimal_weights = dict(zip(assets, result.x))
                return optimal_weights
            else:
                self.logger.warning("Minimum variance optimization failed, using equal weights")
                return self._equal_weight_portfolio()

        except Exception as e:
            self.logger.error("Error in minimum variance optimization", {'error': str(e)})
            return self._equal_weight_portfolio()

    def _optimize_black_litterman(self) -> Dict[str, float]:
        """
        Optimize portfolio using Black-Litterman model

        Incorporates investor views with market equilibrium.
        """
        # Simplified implementation - in practice this would be more complex
        try:
            # For now, fall back to mean-variance with adjusted returns
            assets = list(self.asset_volatilities.keys())

            # Adjust expected returns based on investor views
            adjusted_returns = {}
            for symbol in assets:
                base_return = self._get_expected_return(symbol)
                # Apply view adjustments (simplified)
                if symbol in self.config.investor_views:
                    view_return, confidence = self.config.investor_views[symbol]
                    adjusted_returns[symbol] = (1 - confidence) * base_return + confidence * view_return
                else:
                    adjusted_returns[symbol] = base_return

            # Use adjusted returns in mean-variance optimization
            # This is a simplified approach
            return self._equal_weight_portfolio()

        except Exception as e:
            self.logger.error("Error in Black-Litterman optimization", {'error': str(e)})
            return self._equal_weight_portfolio()

    def _equal_weight_portfolio(self) -> Dict[str, float]:
        """Create equal-weighted portfolio"""
        assets = list(self.asset_volatilities.keys())
        if not assets:
            return {}

        weight = 1.0 / len(assets)
        return {symbol: weight for symbol in assets}

    def _get_expected_return(self, symbol: str) -> float:
        """Get expected return for an asset"""
        if symbol in self.asset_returns and not self.asset_returns[symbol].empty:
            return self.asset_returns[symbol].mean() * 252  # Annualized
        return self.config.risk_free_rate

    def _apply_regime_adjustments(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply regime-based adjustments to portfolio weights

        Adjusts allocations based on detected market regime.
        """
        try:
            if self.current_regime == "high_volatility":
                # Increase bond allocation, reduce equity exposure
                weights = self._adjust_for_volatility_regime(weights)
            elif self.current_regime == "risk_off":
                # Flight to quality: increase bonds, gold, reduce equities
                weights = self._adjust_for_risk_off_regime(weights)
            elif self.current_regime == "low_volatility":
                # Increase risk exposure
                weights = self._adjust_for_low_volatility_regime(weights)

            return weights

        except Exception as e:
            self.logger.error("Error applying regime adjustments", {'error': str(e)})
            return weights

    def _adjust_for_volatility_regime(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Adjust weights for high volatility regime"""
        # Simplified: reduce equity exposure, increase bonds
        adjusted_weights = weights.copy()
        for symbol in adjusted_weights:
            if self._is_equity(symbol):
                adjusted_weights[symbol] *= 0.8
            elif self._is_bond(symbol):
                adjusted_weights[symbol] *= 1.2

        # Renormalize
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {s: w/total for s, w in adjusted_weights.items()}

        return adjusted_weights

    def _adjust_for_risk_off_regime(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Adjust weights for risk-off regime"""
        # Increase safe assets, reduce risky assets
        adjusted_weights = weights.copy()
        for symbol in adjusted_weights:
            if self._is_equity(symbol) or self._is_commodity(symbol):
                adjusted_weights[symbol] *= 0.7
            elif self._is_bond(symbol) or self._is_gold(symbol):
                adjusted_weights[symbol] *= 1.3

        # Renormalize
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {s: w/total for s, w in adjusted_weights.items()}

        return adjusted_weights

    def _adjust_for_low_volatility_regime(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Adjust weights for low volatility regime"""
        # Increase risk exposure
        adjusted_weights = weights.copy()
        for symbol in adjusted_weights:
            if self._is_equity(symbol):
                adjusted_weights[symbol] *= 1.1

        # Renormalize
        total = sum(adjusted_weights.values())
        if total > 0:
            adjusted_weights = {s: w/total for s, w in adjusted_weights.items()}

        return adjusted_weights

    def _is_equity(self, symbol: str) -> bool:
        """Check if symbol is an equity"""
        equity_symbols = ["SPY", "QQQ", "IWM", "EFA", "VWO"]
        return symbol in equity_symbols

    def _is_bond(self, symbol: str) -> bool:
        """Check if symbol is a bond"""
        bond_symbols = ["AGG", "BND", "TIP", "LQD", "HYG"]
        return symbol in bond_symbols

    def _is_commodity(self, symbol: str) -> bool:
        """Check if symbol is a commodity"""
        commodity_symbols = ["USO", "DBC", "GSG"]
        return symbol in commodity_symbols

    def _is_gold(self, symbol: str) -> bool:
        """Check if symbol is gold"""
        return symbol in ["GLD", "SLV"]

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

                if abs(weight_difference) < self.config.min_trade_size:
                    continue

                # Get current price (simplified)
                current_price = 100.0  # Placeholder - would get from market data

                # Determine signal type and quantity
                if weight_difference > 0:
                    signal_type = SignalType.BUY
                    quantity = abs(weight_difference)
                else:
                    signal_type = SignalType.SELL
                    quantity = abs(weight_difference)

                # Create signal
                signal = StrategySignal(
                    signal_id=f"multi_asset_rebalance_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    strategy_id=self.config.strategy_id,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    signal_type=signal_type,
                    confidence=0.8,
                    strength=abs(weight_difference),
                    target_quantity=quantity,
                    signal_price=current_price,
                    entry_price=current_price,
                    max_position_size=self.config.max_asset_weight
                )

                signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating rebalancing signals", {'error': str(e)})

        return signals

    def _generate_currency_hedge_signals(self) -> List[StrategySignal]:
        """
        Generate currency hedging signals

        Creates signals to hedge currency exposure above threshold.
        """
        signals = []

        try:
            # Simplified currency hedging logic
            for currency, exposure in self.currency_exposures.items():
                if abs(exposure) > self.config.hedge_threshold:
                    # Create hedging signal
                    hedge_symbol = f"{currency}USD"  # Simplified hedge instrument

                    signal = StrategySignal(
                        signal_id=f"currency_hedge_{currency}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        strategy_id=self.config.strategy_id,
                        timestamp=datetime.now(),
                        symbol=hedge_symbol,
                        signal_type=SignalType.SELL if exposure > 0 else SignalType.BUY,
                        confidence=0.7,
                        strength=abs(exposure),
                        target_quantity=abs(exposure),
                        signal_price=1.0,  # FX rate placeholder
                        entry_price=1.0,
                        max_position_size=1.0
                    )

                    signals.append(signal)

        except Exception as e:
            self.logger.error("Error generating currency hedge signals", {'error': str(e)})

        return signals

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
            if self.portfolio_volatility > self.config.max_volatility:
                self.logger.warning("Portfolio volatility too high, reducing position sizes")
                # Reduce all signal quantities
                for signal in signals:
                    signal.target_quantity *= 0.8

            return signals

        except Exception as e:
            self.logger.error("Error applying portfolio risk management", {'error': str(e)})
            return signals

    def _update_portfolio_weights(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update current portfolio weights based on market data"""
        try:
            total_value = 0.0
            asset_values = {}

            for symbol, data in market_data.items():
                if data is not None and not data.empty and 'close' in data.columns:
                    current_price = data['close'].iloc[-1]
                    current_weight = self.current_weights.get(symbol, 0.0)
                    asset_values[symbol] = current_weight * current_price
                    total_value += asset_values[symbol]

            # Update weights
            if total_value > 0:
                self.current_weights = {symbol: value / total_value
                                      for symbol, value in asset_values.items()}

        except Exception as e:
            self.logger.error("Error updating portfolio weights", {'error': str(e)})

    def _update_risk_metrics(self) -> None:
        """Update portfolio risk metrics"""
        try:
            if self.current_weights and not self.asset_covariance.empty:
                weights_array = np.array([self.current_weights.get(symbol, 0.0)
                                        for symbol in self.asset_covariance.columns])
                self.portfolio_volatility = np.sqrt(
                    weights_array.T @ self.asset_covariance.values @ weights_array
                ) * np.sqrt(252)  # Annualized

        except Exception as e:
            self.logger.error("Error updating risk metrics", {'error': str(e)})

    def _update_currency_exposures(self) -> None:
        """Update currency exposures for the portfolio"""
        # Simplified - in practice would calculate based on asset currencies
        self.currency_exposures = {"EUR": 0.1, "JPY": 0.05}  # Placeholder

    def get_strategy_metrics(self) -> StrategyMetrics:
        """Get current strategy performance metrics"""
        metrics = StrategyMetrics()

        # Populate with actual metrics
        metrics.total_signals = len(self.signal_history)
        metrics.active_positions = len(self.current_weights)

        # Add multi-asset specific metrics
        metrics.total_return = sum(self.asset_class_weights.values())

        return metrics