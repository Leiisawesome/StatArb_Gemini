"""
Enhanced Pairs Trading Strategy with ISystemComponent Integration
===============================================================

Professional pairs trading strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Advanced pair selection and validation
- Cointegration-based spread trading
- Dynamic hedge ratio estimation
- Professional risk management integration
- Comprehensive performance tracking

Key Features:
- Statistical pair selection using correlation and cointegration
- Dynamic hedge ratio calculation
- Spread mean reversion detection
- Risk-adjusted position sizing
- Pair performance monitoring
- Transaction cost optimization

Academic Foundations:
- Gatev et al. (2006) pairs trading strategies
- Vidyamurthy (2004) pairs trading quantitative methods
- Engle & Granger (1987) cointegration analysis

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from statsmodels.tsa.stattools import coint

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import PairsConfig

logger = logging.getLogger(__name__)

# ✅ PairsConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only


class PairStatus(Enum):
    """Pair trading status"""
    NEUTRAL = "neutral"
    LONG_SPREAD = "long_spread"      # Long stock1, short stock2
    SHORT_SPREAD = "short_spread"    # Short stock1, long stock2
    MONITORING = "monitoring"


@dataclass
class PairMetrics:
    """Metrics for a trading pair"""

    stock1: str
    stock2: str
    correlation: float
    cointegration_pvalue: float
    hedge_ratio: float

    # Spread statistics
    spread_mean: float = 0.0
    spread_std: float = 1.0
    current_zscore: float = 0.0

    # Trading metrics
    entry_zscore: float = 0.0
    trades_count: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0

    # Status
    status: PairStatus = PairStatus.NEUTRAL
    entry_time: Optional[datetime] = None
    last_update: Optional[datetime] = None


class EnhancedPairsTradingStrategy(EnhancedBaseStrategy):
    """
    Enhanced Pairs Trading Strategy with ISystemComponent Integration

    Professional pairs trading strategy that provides:
    - ISystemComponent interface compliance
    - Advanced pair selection and validation
    - Cointegration-based spread trading
    - Dynamic hedge ratio estimation
    - Comprehensive performance tracking and risk management
    """

    def __init__(self, config: PairsConfig):
        """Initialize enhanced pairs trading strategy"""

        # Initialize base strategy
        super().__init__(config)
        self.config: PairsConfig = config

        # Strategy-specific state (analysis data - NOT position tracking)
        self.market_data: Dict[str, pd.DataFrame] = {}
        # Note: selected_pairs and active_pairs track pair analysis metrics
        # Actual position tracking should use PositionBook (SSOT) and Risk Manager
        self.selected_pairs: Dict[str, PairMetrics] = {}
        self.active_pairs: Dict[str, PairMetrics] = {}

        # Pair analysis data
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.cointegration_results: Dict[Tuple[str, str], Dict[str, Any]] = {}

        # Performance tracking
        self.pair_performance: Dict[str, Dict[str, float]] = {}
        self.trade_history: List[Dict[str, Any]] = []

        logger.info(f"🧠 Enhanced Pairs Trading Strategy {self.strategy_id} initialized")

    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""

        try:
            logger.info(f"🔄 Initializing Pairs Trading components for {self.strategy_id}...")

            # Validate asset universe
            if len(self.config.asset_universe) < 2:
                logger.error("❌ Asset universe must contain at least 2 assets")
                return False

            # Initialize data structures
            self._initialize_data_structures()

            logger.info(f"✅ Pairs Trading components initialized for {len(self.config.asset_universe)} assets")
            return True

        except Exception as e:
            logger.error(f"❌ Pairs Trading component initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""

        try:
            logger.info(f"🚀 Starting Pairs Trading operations for {self.strategy_id}...")
            return True

        except Exception as e:
            logger.error(f"❌ Pairs Trading operations start failed: {e}")
            return False

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""

        try:
            logger.info(f"🔄 Stopping Pairs Trading operations for {self.strategy_id}...")

            # Close all active pairs
            await self._close_all_pairs()

            logger.info(f"✅ Pairs Trading operations stopped")

        except Exception as e:
            logger.error(f"❌ Pairs Trading operations stop failed: {e}")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""

        try:
            health_metrics = {
                'strategy_healthy': True,
                'selected_pairs': len(self.selected_pairs),
                'active_pairs': len(self.active_pairs),
                'avg_correlation': self._calculate_avg_correlation(),
                'cointegrated_pairs': len(self.cointegration_results)
            }

            # Check for unhealthy conditions
            if len(self.selected_pairs) == 0:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "No pairs selected"

            avg_correlation = health_metrics['avg_correlation']
            if avg_correlation < self.config.min_correlation:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = f"Low average correlation: {avg_correlation:.3f}"

            return health_metrics

        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""

        return {
            'strategy_type': 'Enhanced Pairs Trading',
            'asset_universe_size': len(self.config.asset_universe),
            'min_correlation': self.config.min_correlation,
            'entry_zscore': self.config.entry_zscore,
            'exit_zscore': self.config.exit_zscore,
            'max_pairs': self.config.max_pairs,
            'position_size_pct': self.config.position_size_pct
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""

        try:
            # Validate thresholds
            if self.config.entry_zscore <= self.config.exit_zscore:
                logger.error("Entry Z-score must be greater than exit Z-score")
                return False

            if self.config.stop_loss_zscore <= self.config.entry_zscore:
                logger.error("Stop loss Z-score must be greater than entry Z-score")
                return False

            # Validate correlation threshold
            if self.config.min_correlation <= 0 or self.config.min_correlation > 1:
                logger.error("Minimum correlation must be between 0 and 1")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================

    def _validate_enriched_data(self, enriched_data: Dict[str, pd.DataFrame]) -> None:
        """
        Validate that data is enriched with required features (Rule 3 Phase 4)

        Pairs trading strategy requires OHLCV data for spread calculation.
        Returns are not calculated here (spread logic is strategy-specific).

        Args:
            enriched_data: Dict[symbol, enriched DataFrame]

        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'close',            # Close prices (for spreads)
            'volume'            # Volume (for liquidity checks)
        ]

        for pair in self.selected_pairs:
            for symbol in pair:
                if symbol not in enriched_data:
                    continue

                data = enriched_data[symbol]
                if data.empty:
                    raise ValueError(f"{symbol} has empty DataFrame")

                missing = [col for col in required_features if col not in data.columns]
                if missing:
                    available_cols = list(data.columns[:20])
                    raise ValueError(
                        f"{symbol} missing required features: {missing}. "
                        f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3). "
                        f"Available columns: {available_cols}"
                    )

            logger.debug(f"✅ Pair {pair} enriched data validated")

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate pairs trading signals from ENRICHED data (Rule 3 Phase 4)

        **CRITICAL CHANGE:** This method now receives enriched data from the
        ProcessingPipelineOrchestrator. Spread calculations are strategy-specific
        and appropriately kept in the strategy.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV]

        Returns:
            List[StrategySignal]: Generated pairs trading signals
        """
        start_time = datetime.now()
        signals = []

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data
            self._update_market_data(enriched_data)

            # Update pair selection if needed
            await self._update_pair_selection()

            # Update spread calculations
            self._update_spread_calculations()

            # Generate entry signals
            entry_signals = await self._generate_entry_signals()
            signals.extend(entry_signals)

            # Generate exit signals
            exit_signals = await self._generate_exit_signals()
            signals.extend(exit_signals)

            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            logger.info(f"📊 Generated {len(signals)} Pairs Trading signals in {generation_time:.3f}s")

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""

        try:
            # Update market data
            self._update_market_data(market_data)

            # Update spread calculations
            self._update_spread_calculations()

            # Check for stop losses
            await self._check_stop_losses()

            # Update pair correlations
            self._update_pair_correlations()

        except Exception as e:
            self._log_error("Position update failed", e)

    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""

        try:
            # For pairs trading, use configured position size
            return self.config.position_size_pct

        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0

    # ========================================
    # PAIR SELECTION METHODS
    # ========================================

    async def _update_pair_selection(self) -> None:
        """Update pair selection based on current market data"""

        try:
            # Calculate correlation matrix
            self._calculate_correlation_matrix()

            # Test cointegration for highly correlated pairs
            await self._test_cointegration()

            # Select best pairs
            self._select_trading_pairs()

        except Exception as e:
            self._log_error("Pair selection update failed", e)

    def _calculate_correlation_matrix(self) -> None:
        """Calculate correlation matrix for asset universe"""

        try:
            # Collect price data for all assets
            price_data = {}

            for symbol in self.config.asset_universe:
                if symbol in self.market_data and len(self.market_data[symbol]) >= self.config.lookback_period:
                    prices = self.market_data[symbol]['close'].tail(self.config.lookback_period)
                    price_data[symbol] = prices

            if len(price_data) < 2:
                return

            # Create DataFrame and calculate correlations
            df = pd.DataFrame(price_data)
            self.correlation_matrix = df.corr()

        except Exception as e:
            logger.error(f"Correlation matrix calculation failed: {e}")

    async def _test_cointegration(self) -> None:
        """Test cointegration for highly correlated pairs"""

        try:
            if self.correlation_matrix is None:
                return

            # Find highly correlated pairs
            for i, stock1 in enumerate(self.correlation_matrix.index):
                for j, stock2 in enumerate(self.correlation_matrix.columns):
                    if i < j:  # Avoid duplicate pairs
                        correlation = self.correlation_matrix.loc[stock1, stock2]

                        if abs(correlation) >= self.config.min_correlation:
                            # Test cointegration
                            coint_result = await self._test_pair_cointegration(stock1, stock2)
                            if coint_result:
                                self.cointegration_results[(stock1, stock2)] = coint_result

        except Exception as e:
            logger.error(f"Cointegration testing failed: {e}")

    async def _test_pair_cointegration(self, stock1: str, stock2: str) -> Optional[Dict[str, Any]]:
        """Test cointegration between two stocks"""

        try:
            if stock1 not in self.market_data or stock2 not in self.market_data:
                return None

            # Get price series
            prices1 = self.market_data[stock1]['close'].tail(self.config.lookback_period)
            prices2 = self.market_data[stock2]['close'].tail(self.config.lookback_period)

            # Align data
            aligned_data = pd.concat([prices1, prices2], axis=1, join='inner')
            aligned_data.columns = [stock1, stock2]

            if len(aligned_data) < 50:  # Minimum data requirement
                return None

            # Perform cointegration test
            score, p_value, _ = coint(aligned_data[stock1], aligned_data[stock2])

            if p_value <= self.config.cointegration_threshold:
                # Calculate hedge ratio using linear regression
                from sklearn.linear_model import LinearRegression

                X = aligned_data[stock1].values.reshape(-1, 1)
                y = aligned_data[stock2].values

                reg = LinearRegression().fit(X, y)
                hedge_ratio = reg.coef_[0]

                # Calculate spread statistics
                spread = aligned_data[stock2] - hedge_ratio * aligned_data[stock1]
                spread_mean = spread.mean()
                spread_std = spread.std()

                return {
                    'p_value': p_value,
                    'hedge_ratio': hedge_ratio,
                    'spread_mean': spread_mean,
                    'spread_std': spread_std,
                    'correlation': self.correlation_matrix.loc[stock1, stock2],
                    'last_updated': datetime.now()
                }

            return None

        except Exception as e:
            logger.error(f"Cointegration test failed for {stock1}-{stock2}: {e}")
            return None

    def _select_trading_pairs(self) -> None:
        """Select the best pairs for trading"""

        try:
            # Clear existing selections
            self.selected_pairs.clear()

            # Sort cointegrated pairs by quality
            sorted_pairs = sorted(
                self.cointegration_results.items(),
                key=lambda x: (abs(x[1]['correlation']), -x[1]['p_value'])
            )

            # Select top pairs up to maximum
            for (stock1, stock2), coint_data in sorted_pairs[:self.config.max_pairs * 2]:
                pair_id = f"{stock1}_{stock2}"

                pair_metrics = PairMetrics(
                    stock1=stock1,
                    stock2=stock2,
                    correlation=coint_data['correlation'],
                    cointegration_pvalue=coint_data['p_value'],
                    hedge_ratio=coint_data['hedge_ratio'],
                    spread_mean=coint_data['spread_mean'],
                    spread_std=coint_data['spread_std'],
                    last_update=datetime.now()
                )

                self.selected_pairs[pair_id] = pair_metrics

            logger.info(f"📈 Selected {len(self.selected_pairs)} pairs for trading")

        except Exception as e:
            logger.error(f"Pair selection failed: {e}")

    # ========================================
    # SIGNAL GENERATION METHODS
    # ========================================

    async def _generate_entry_signals(self) -> List[StrategySignal]:
        """Generate entry signals for pairs"""

        signals = []

        try:
            for pair_id, pair_metrics in self.selected_pairs.items():
                # Skip if already active
                if pair_id in self.active_pairs:
                    continue

                # Skip if maximum pairs reached
                if len(self.active_pairs) >= self.config.max_pairs:
                    break

                # Check for entry conditions
                zscore = pair_metrics.current_zscore

                if abs(zscore) >= self.config.entry_zscore:
                    # Generate pair signals
                    pair_signals = self._create_pair_entry_signals(pair_metrics, zscore)
                    signals.extend(pair_signals)

                    # Mark pair as active
                    pair_metrics.status = PairStatus.LONG_SPREAD if zscore < 0 else PairStatus.SHORT_SPREAD
                    pair_metrics.entry_time = datetime.now()
                    pair_metrics.entry_zscore = zscore
                    self.active_pairs[pair_id] = pair_metrics

            return signals

        except Exception as e:
            self._log_error("Entry signal generation failed", e)
            return []

    async def _generate_exit_signals(self) -> List[StrategySignal]:
        """Generate exit signals for active pairs"""

        signals = []

        try:
            pairs_to_close = []

            for pair_id, pair_metrics in self.active_pairs.items():
                zscore = pair_metrics.current_zscore

                should_exit = False
                exit_reason = ""

                # Mean reversion exit
                if abs(zscore) <= self.config.exit_zscore:
                    should_exit = True
                    exit_reason = "mean_reversion"

                # Stop loss exit
                elif abs(zscore) >= self.config.stop_loss_zscore:
                    should_exit = True
                    exit_reason = "stop_loss"

                # Time-based exit
                elif pair_metrics.entry_time:
                    holding_period = (datetime.now() - pair_metrics.entry_time).days
                    if holding_period >= self.config.max_holding_period:
                        should_exit = True
                        exit_reason = "max_holding_period"

                # Correlation breakdown
                elif abs(pair_metrics.correlation) < self.config.correlation_threshold:
                    should_exit = True
                    exit_reason = "correlation_breakdown"

                if should_exit:
                    # Generate exit signals
                    exit_signals = self._create_pair_exit_signals(pair_metrics, exit_reason)
                    signals.extend(exit_signals)

                    pairs_to_close.append(pair_id)

                    logger.info(f"📉 Exit signal generated for pair {pair_id}: {exit_reason}")

            # Clean up closed pairs
            for pair_id in pairs_to_close:
                if pair_id in self.active_pairs:
                    del self.active_pairs[pair_id]

            return signals

        except Exception as e:
            self._log_error("Exit signal generation failed", e)
            return []

    def _create_pair_entry_signals(self, pair_metrics: PairMetrics, zscore: float) -> List[StrategySignal]:
        """Create entry signals for a pair"""

        signals = []

        try:
            stock1 = pair_metrics.stock1
            stock2 = pair_metrics.stock2

            if zscore < -self.config.entry_zscore:
                # Spread is below mean - Long spread (Buy stock1, Sell stock2)

                signal1 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock1,
                    signal_type=SignalType.BUY,
                    strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
                    confidence=0.8,
                    target_weight=self.config.position_size_pct,  # Use as percentage weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'pair_stock': stock2,
                        'zscore': zscore,
                        'hedge_ratio': pair_metrics.hedge_ratio,
                        'spread_direction': 'long'
                    }
                )

                signal2 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock2,
                    signal_type=SignalType.SELL,
                    strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
                    confidence=0.8,
                    target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),  # Hedge-adjusted weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'pair_stock': stock1,
                        'zscore': zscore,
                        'hedge_ratio': pair_metrics.hedge_ratio,
                        'spread_direction': 'long'
                    }
                )

            else:
                # Spread is above mean - Short spread (Sell stock1, Buy stock2)

                signal1 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock1,
                    signal_type=SignalType.SELL,
                    strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
                    confidence=0.8,
                    target_weight=self.config.position_size_pct,  # Use as percentage weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'pair_stock': stock2,
                        'zscore': zscore,
                        'hedge_ratio': pair_metrics.hedge_ratio,
                        'spread_direction': 'short'
                    }
                )

                signal2 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock2,
                    signal_type=SignalType.BUY,
                    strength=min(abs(zscore) / self.config.entry_zscore, 1.0),
                    confidence=0.8,
                    target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),  # Hedge-adjusted weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'pair_stock': stock1,
                        'zscore': zscore,
                        'hedge_ratio': pair_metrics.hedge_ratio,
                        'spread_direction': 'short'
                    }
                )

            signals.extend([signal1, signal2])

            return signals

        except Exception as e:
            self._log_error("Pair entry signal creation failed", e)
            return []

    def _create_pair_exit_signals(self, pair_metrics: PairMetrics, exit_reason: str) -> List[StrategySignal]:
        """Create exit signals for a pair"""

        signals = []

        try:
            stock1 = pair_metrics.stock1
            stock2 = pair_metrics.stock2

            # Create exit signals (reverse of entry)
            if pair_metrics.status == PairStatus.LONG_SPREAD:
                # Close long spread (Sell stock1, Buy stock2)

                signal1 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock1,
                    signal_type=SignalType.SELL,
                    strength=1.0,
                    confidence=0.9,
                    target_weight=self.config.position_size_pct,  # Use as percentage weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'action': 'exit',
                        'exit_reason': exit_reason,
                        'spread_direction': 'long'
                    }
                )

                signal2 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock2,
                    signal_type=SignalType.BUY,
                    strength=1.0,
                    confidence=0.9,
                    target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),  # Hedge-adjusted weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'action': 'exit',
                        'exit_reason': exit_reason,
                        'spread_direction': 'long'
                    }
                )

            else:  # SHORT_SPREAD
                # Close short spread (Buy stock1, Sell stock2)

                signal1 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock1,
                    signal_type=SignalType.BUY,
                    strength=1.0,
                    confidence=0.9,
                    target_weight=self.config.position_size_pct,  # Use as percentage weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'action': 'exit',
                        'exit_reason': exit_reason,
                        'spread_direction': 'short'
                    }
                )

                signal2 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=stock2,
                    signal_type=SignalType.SELL,
                    strength=1.0,
                    confidence=0.9,
                    target_weight=self.config.position_size_pct * abs(pair_metrics.hedge_ratio),  # Hedge-adjusted weight

                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'pair_id': f"{stock1}_{stock2}",
                        'action': 'exit',
                        'exit_reason': exit_reason,
                        'spread_direction': 'short'
                    }
                )

            signals.extend([signal1, signal2])

            return signals

        except Exception as e:
            self._log_error("Pair exit signal creation failed", e)
            return []

    # ========================================
    # HELPER METHODS
    # ========================================

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""

        for symbol, data in market_data.items():
            if symbol in self.config.asset_universe:
                self.market_data[symbol] = data

    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""

        self.market_data.clear()
        self.selected_pairs.clear()
        self.active_pairs.clear()
        self.cointegration_results.clear()
        self.pair_performance.clear()
        self.trade_history.clear()

    def _update_spread_calculations(self) -> None:
        """Update spread calculations for all pairs"""

        try:
            for pair_id, pair_metrics in self.selected_pairs.items():
                current_zscore = self._calculate_current_zscore(pair_metrics)
                pair_metrics.current_zscore = current_zscore
                pair_metrics.last_update = datetime.now()

        except Exception as e:
            logger.error(f"Spread calculation update failed: {e}")

    def _calculate_current_zscore(self, pair_metrics: PairMetrics) -> float:
        """Calculate current Z-score for a pair"""

        try:
            stock1 = pair_metrics.stock1
            stock2 = pair_metrics.stock2

            if stock1 not in self.market_data or stock2 not in self.market_data:
                return 0.0

            # Get current prices
            price1 = self.market_data[stock1]['close'].iloc[-1]
            price2 = self.market_data[stock2]['close'].iloc[-1]

            # Calculate current spread
            current_spread = price2 - pair_metrics.hedge_ratio * price1

            # Calculate Z-score
            if pair_metrics.spread_std != 0:
                zscore = (current_spread - pair_metrics.spread_mean) / pair_metrics.spread_std
            else:
                zscore = 0.0

            return zscore

        except Exception as e:
            logger.error(f"Z-score calculation failed for {pair_metrics.stock1}-{pair_metrics.stock2}: {e}")
            return 0.0

    def _calculate_avg_correlation(self) -> float:
        """Calculate average correlation of selected pairs"""

        if not self.selected_pairs:
            return 0.0

        correlations = [pair.correlation for pair in self.selected_pairs.values()]
        return np.mean(np.abs(correlations))

    async def _check_stop_losses(self) -> None:
        """Check stop losses for active pairs"""

        # Placeholder for stop loss checking

    def _update_pair_correlations(self) -> None:
        """Update correlations for active pairs"""

        # Placeholder for correlation updates

    async def _close_all_pairs(self) -> None:
        """Close all active pairs"""

        logger.info(f"🔄 Closing {len(self.active_pairs)} active pairs")
        self.active_pairs.clear()

    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================

    def get_pairs_trading_summary(self) -> Dict[str, Any]:
        """Get comprehensive pairs trading strategy summary"""

        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Pairs Trading',
            'selected_pairs': len(self.selected_pairs),
            'active_pairs': len(self.active_pairs),
            'avg_correlation': self._calculate_avg_correlation(),
            'cointegrated_pairs': len(self.cointegration_results),
            'performance_summary': self.get_performance_summary(),
            'pair_details': {
                pair_id: {
                    'stock1': pair.stock1,
                    'stock2': pair.stock2,
                    'correlation': pair.correlation,
                    'current_zscore': pair.current_zscore,
                    'status': pair.status.value,
                    'trades_count': pair.trades_count,
                    'winning_trades': pair.winning_trades
                }
                for pair_id, pair in self.selected_pairs.items()
            },
            'active_pair_details': {
                pair_id: {
                    'stock1': pair.stock1,
                    'stock2': pair.stock2,
                    'entry_zscore': pair.entry_zscore,
                    'current_zscore': pair.current_zscore,
                    'status': pair.status.value,
                    'entry_time': pair.entry_time.isoformat() if pair.entry_time else None
                }
                for pair_id, pair in self.active_pairs.items()
            }
        }
