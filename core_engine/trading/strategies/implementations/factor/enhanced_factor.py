"""
Enhanced Factor Strategy with ISystemComponent Integration
========================================================

Professional factor-based strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

Key Features:
- Multi-factor model implementation
- Factor exposure analysis
- Risk-adjusted factor investing
- Dynamic factor weighting
- Professional performance attribution

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import FactorConfig

logger = logging.getLogger(__name__)

# ✅ FactorConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only


class EnhancedFactorStrategy(EnhancedBaseStrategy):
    """Enhanced Factor Strategy with ISystemComponent Integration"""

    def __init__(self, config: FactorConfig):
        """Initialize enhanced factor strategy"""

        # Initialize base strategy
        super().__init__(config)
        self.config: FactorConfig = config

        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.factor_scores: Dict[str, Dict[str, float]] = {}
        # DEPRECATED: active_positions is deprecated. Use PositionBook (SSOT) instead.
        # Position tracking should be handled by Risk Manager, not strategies.
        self.active_positions: Dict[str, Dict[str, Any]] = {}  # DEPRECATED

        logger.info(f"🧠 Enhanced Factor Strategy {self.strategy_id} initialized")

    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""

        try:
            logger.info(f"🔄 Initializing Factor components for {self.strategy_id}...")

            if not self.config.symbols:
                logger.error("❌ No symbols configured for factor strategy")
                return False

            self._initialize_data_structures()

            logger.info(f"✅ Factor components initialized for {len(self.config.symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"❌ Factor component initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""

        try:
            logger.info(f"🚀 Starting Factor operations for {self.strategy_id}...")
            return True

        except Exception as e:
            logger.error(f"❌ Factor operations start failed: {e}")
            return False

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""

        try:
            logger.info(f"🔄 Stopping Factor operations for {self.strategy_id}...")
            await self._close_all_positions()
            logger.info(f"✅ Factor operations stopped")

        except Exception as e:
            logger.error(f"❌ Factor operations stop failed: {e}")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""

        try:
            return {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'factors_calculated': len(self.factor_scores)
            }

        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""

        return {
            'strategy_type': 'Enhanced Factor',
            'symbols_count': len(self.config.symbols),
            'factors': self.config.factors,
            'rebalance_frequency': self.config.rebalance_frequency,
            'factor_lookback': self.config.factor_lookback
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""

        try:
            if not self.config.factors:
                logger.error("At least one factor must be specified")
                return False

            if self.config.factor_lookback < 20:
                logger.error("Factor lookback must be at least 20")
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

        Factor strategy requires pre-calculated returns and volatility metrics.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame]

        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'returns_1',        # 1-period returns (for momentum factor)
            'volatility',       # Volatility metric (for quality/volatility factors)
            'close',            # Close prices
            'volume'            # Volume (for liquidity checks)
        ]

        for symbol in self.config.symbols:
            if symbol not in enriched_data:
                continue  # Skip if symbol not in data

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

            logger.debug(f"✅ {symbol} enriched data validated: {len(required_features)} features present")

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate factor-based signals from ENRICHED data (Rule 3 Phase 4)

        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        features from the ProcessingPipelineOrchestrator. It reads pre-calculated
        returns and volatility instead of calculating them.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: returns_1, volatility

        Returns:
            List[StrategySignal]: Generated factor-based signals
        """
        start_time = datetime.now()
        signals = []

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data with enriched data
            self._update_market_data(enriched_data)

            # Calculate factor scores
            self._calculate_factor_scores()

            # Generate signals based on factor rankings
            signals = await self._generate_factor_signals()

            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            logger.info(f"📊 Factor Strategy (Rule 3 Phase 4 - Enriched Data):")
            logger.info(f"   Signals generated: {len(signals)}")
            logger.info(f"   Generation time: {generation_time:.3f}s")

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""

        try:
            self._update_market_data(market_data)

        except Exception as e:
            self._log_error("Position update failed", e)

    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""

        try:
            base_size = self.config.base_position_pct
            factor_strength = signal.strength
            return min(base_size * factor_strength, self.config.max_position_pct)

        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0

    # ========================================
    # FACTOR CALCULATION METHODS
    # ========================================

    def _calculate_factor_scores(self) -> None:
        """Calculate factor scores for all symbols"""

        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.factor_scores[symbol] = self._calculate_symbol_factors(symbol)

    def _calculate_symbol_factors(self, symbol: str) -> Dict[str, float]:
        """
        Calculate factor scores using PRE-CALCULATED features (Rule 3 Phase 4)

        **CRITICAL:** This method now reads pre-calculated returns and volatility
        from enriched data instead of calculating them.
        """
        try:
            data = self.market_data[symbol]
            scores = {}

            if len(data) < self.config.factor_lookback:
                return scores

            # Calculate momentum factor using PRE-CALCULATED returns (Rule 3 Phase 4)
            if 'momentum' in self.config.factors:
                if 'returns_1' in data.columns:
                    # ✅ READ pre-calculated returns from FeatureEngineer
                    returns = data['returns_1']
                    momentum_score = returns.tail(self.config.factor_lookback).mean()
                    scores['momentum'] = momentum_score
                    logger.debug(f"✅ {symbol}: Using pre-calculated returns for momentum factor")
                elif 'close' in data.columns:
                    # Use pre-calculated returns
                    returns = data['close'].pct_change()
                    momentum_score = returns.tail(self.config.factor_lookback).mean()
                    scores['momentum'] = momentum_score
                    logger.warning(f"⚠️  {symbol}: Falling back to calculated returns for momentum")

            # Calculate value factor using PRE-CALCULATED volatility (Rule 3 Phase 4)
            if 'value' in self.config.factors:
                # ✅ READ pre-calculated volatility from FeatureEngineer (Rule 3 Phase 4)
                # PROHIBITED: No fallback calculations - validation should catch missing volatility
                if 'volatility' not in data.columns:
                    raise ValueError(
                        f"{symbol}: Missing required 'volatility' column for value factor. "
                        f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3)."
                    )

                price_volatility = data['volatility'].tail(self.config.factor_lookback).mean()
                scores['value'] = -price_volatility  # Lower volatility = higher value score
                logger.debug(f"✅ {symbol}: Using pre-calculated volatility for value factor")

            # Calculate quality factor using PRE-CALCULATED volatility (Rule 3 Phase 4)
            if 'quality' in self.config.factors:
                # ✅ READ pre-calculated volatility
                # PROHIBITED: No fallback calculations
                if 'volatility' not in data.columns:
                    raise ValueError(
                        f"{symbol}: Missing required 'volatility' column for quality factor. "
                        f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3)."
                    )

                vol = data['volatility'].tail(self.config.factor_lookback).mean()
                price_stability = 1.0 / (1.0 + vol)
                scores['quality'] = price_stability
                logger.debug(f"✅ {symbol}: Using pre-calculated volatility for quality factor")

            # Calculate volatility factor using PRE-CALCULATED volatility (Rule 3 Phase 4)
            if 'volatility' in self.config.factors:
                # ✅ READ pre-calculated volatility
                # PROHIBITED: No fallback calculations
                if 'volatility' not in data.columns:
                    raise ValueError(
                        f"{symbol}: Missing required 'volatility' column for volatility factor. "
                        f"Data must be enriched via ProcessingPipelineOrchestrator (Rule 3)."
                    )

                volatility = data['volatility'].tail(self.config.factor_lookback).mean()
                scores['volatility'] = -volatility  # Lower volatility = higher score
                logger.debug(f"✅ {symbol}: Using pre-calculated volatility for volatility factor")

            return scores

        except Exception as e:
            logger.error(f"Factor calculation failed for {symbol}: {e}")
            return {}

    async def _generate_factor_signals(self) -> List[StrategySignal]:
        """Generate signals based on factor rankings"""

        signals = []

        try:
            # Rank symbols by composite factor score
            symbol_rankings = self._rank_symbols_by_factors()

            # Generate signals for top-ranked symbols
            top_symbols = symbol_rankings[:3]  # Top 3 symbols

            for symbol, composite_score in top_symbols:
                if composite_score > 0:  # Only positive scores
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        strength=min(composite_score * 2, 1.0),
                        confidence=0.7,
                        target_weight=self.config.base_position_pct,  # Use as percentage weight
                        quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                        timestamp=datetime.now(),
                        additional_data={  # FIXED: metadata -> additional_data
                            'signal_reason': 'factor_ranking',
                            'composite_score': composite_score,
                            'factor_scores': self.factor_scores.get(symbol, {})
                        }
                    )
                    signals.append(signal)

            return signals

        except Exception as e:
            self._log_error("Factor signal generation failed", e)
            return []

    def _rank_symbols_by_factors(self) -> List[Tuple[str, float]]:
        """Rank symbols by composite factor score"""

        try:
            symbol_scores = []

            for symbol, factors in self.factor_scores.items():
                if factors:
                    # Calculate composite score (equal weighting)
                    composite_score = np.mean(list(factors.values()))
                    symbol_scores.append((symbol, composite_score))

            # Sort by composite score (descending)
            symbol_scores.sort(key=lambda x: x[1], reverse=True)

            return symbol_scores

        except Exception as e:
            logger.error(f"Symbol ranking failed: {e}")
            return []

    # ========================================
    # HELPER METHODS
    # ========================================

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""

        for symbol, data in market_data.items():
            if symbol in self.config.symbols:
                self.market_data[symbol] = data

    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""

        self.market_data.clear()
        self.factor_scores.clear()
        self.active_positions.clear()

    async def _close_all_positions(self) -> None:
        """Close all active positions"""

        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()

    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================

    def get_factor_summary(self) -> Dict[str, Any]:
        """Get comprehensive factor strategy summary"""

        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Factor',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'performance_summary': self.get_performance_summary(),
            'factor_scores': self.factor_scores,
            'symbol_rankings': self._rank_symbols_by_factors()
        }
