"""
Enhanced Arbitrage Strategy with ISystemComponent Integration
===========================================================

Professional arbitrage strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Cross-asset arbitrage opportunity detection
- Real-time price discrepancy analysis
- Risk-managed arbitrage execution
- Professional performance tracking

Key Features:
- Multi-asset arbitrage detection
- Price convergence analysis
- Transaction cost-aware execution
- Risk-adjusted position sizing
- Latency-sensitive opportunity capture
- Statistical arbitrage validation

Academic Foundations:
- Fama (1970) efficient market hypothesis
- Roll (1984) bid-ask spread analysis
- Hasbrouck (1991) price discovery mechanisms

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...contracts import StrategySignal
from core_engine.type_definitions.strategy import SignalType

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import ArbitrageConfig

logger = logging.getLogger(__name__)

# ✅ ArbitrageConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only

class ArbitrageType(Enum):
    """Types of arbitrage opportunities"""
    PRICE_ARBITRAGE = "price_arbitrage"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    CROSS_ASSET_ARBITRAGE = "cross_asset_arbitrage"
    TEMPORAL_ARBITRAGE = "temporal_arbitrage"

class EnhancedArbitrageStrategy(EnhancedBaseStrategy):
    """
    Enhanced Arbitrage Strategy with ISystemComponent Integration

    Professional arbitrage strategy that provides:
    - ISystemComponent interface compliance
    - Cross-asset arbitrage opportunity detection
    - Real-time price discrepancy analysis
    - Risk-managed arbitrage execution
    """

    def __init__(self, config: ArbitrageConfig):
        """Initialize enhanced arbitrage strategy"""

        # Initialize base strategy
        super().__init__(config)
        self.config: ArbitrageConfig = config

        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.price_data: Dict[str, float] = {}
        # Note: arbitrage_opportunities tracks detected opportunities, not positions
        # Position tracking should use PositionBook (SSOT) and Risk Manager
        self.arbitrage_opportunities: Dict[str, Dict[str, Any]] = {}

        # Performance tracking
        self.executed_arbitrages: List[Dict[str, Any]] = []
        self.missed_opportunities: List[Dict[str, Any]] = []

        logger.info(f"🧠 Enhanced Arbitrage Strategy {self.strategy_id} initialized")

    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================

    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""

        try:
            logger.info(f"🔄 Initializing Arbitrage components for {self.strategy_id}...")

            # Validate arbitrage pairs
            if not self.config.arbitrage_pairs:
                logger.error("❌ No arbitrage pairs configured")
                return False

            # Initialize data structures
            self._initialize_data_structures()

            logger.info(f"✅ Arbitrage components initialized for {len(self.config.arbitrage_pairs)} pairs")
            return True

        except Exception as e:
            logger.error(f"❌ Arbitrage component initialization failed: {e}")
            return False

    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""

        try:
            logger.info(f"🚀 Starting Arbitrage operations for {self.strategy_id}...")
            return True

        except Exception as e:
            logger.error(f"❌ Arbitrage operations start failed: {e}")
            return False

    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""

        try:
            logger.info(f"🔄 Stopping Arbitrage operations for {self.strategy_id}...")
            logger.info(f"✅ Arbitrage operations stopped")

        except Exception as e:
            logger.error(f"❌ Arbitrage operations stop failed: {e}")

    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""

        try:
            return {
                'strategy_healthy': True,
                'arbitrage_pairs': len(self.config.arbitrage_pairs),
                'active_opportunities': len(self.arbitrage_opportunities),
                'executed_arbitrages': len(self.executed_arbitrages)
            }

        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}

    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""

        return {
            'strategy_type': 'Enhanced Arbitrage',
            'arbitrage_pairs_count': len(self.config.arbitrage_pairs),
            'min_price_discrepancy': self.config.min_price_discrepancy,
            'max_execution_time': self.config.max_execution_time,
            'confidence_threshold': self.config.confidence_threshold
        }

    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""

        try:
            if self.config.min_price_discrepancy <= 0:
                logger.error("Minimum price discrepancy must be positive")
                return False

            if self.config.max_execution_time <= 0:
                logger.error("Maximum execution time must be positive")
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

        Arbitrage strategy requires OHLCV data for price discrepancy detection.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame]

        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'close',            # Close prices (for arbitrage opportunities)
            'volume'            # Volume (for liquidity checks)
        ]

        # Iterate over enriched_data keys instead of self.config.symbols
        # (ArbitrageConfig uses arbitrage_pairs, not symbols)
        for symbol in enriched_data.keys():
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

            logger.debug(f"✅ {symbol} enriched data validated")

    async def generate_signals(self, enriched_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """
        Generate arbitrage signals from ENRICHED data (Rule 3 Phase 4)

        **CRITICAL CHANGE:** This method now receives enriched data from the
        ProcessingPipelineOrchestrator. Arbitrage calculations are strategy-specific
        and appropriately kept in the strategy.

        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV]

        Returns:
            List[StrategySignal]: Generated arbitrage signals
        """
        start_time = datetime.now()
        signals = []

        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)

            # Update market data
            self._update_market_data(enriched_data)

            # Detect arbitrage opportunities
            opportunities = self._detect_arbitrage_opportunities()

            # Generate signals for valid opportunities
            for opp_id, opportunity in opportunities.items():
                if self._validate_opportunity(opportunity):
                    opp_signals = self._create_arbitrage_signals(opportunity)
                    signals.extend(opp_signals)

            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)

            logger.info(f"📊 Generated {len(signals)} Arbitrage signals in {generation_time:.3f}s")

            return signals

        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []

    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""

        try:
            # Update market data
            self._update_market_data(market_data)

            # Check for opportunity expiration
            self._check_opportunity_expiration()

        except Exception as e:
            self._log_error("Position update failed", e)

    # ========================================
    # ARBITRAGE DETECTION METHODS
    # ========================================

    def _detect_arbitrage_opportunities(self) -> Dict[str, Dict[str, Any]]:
        """Detect arbitrage opportunities across asset pairs"""

        opportunities = {}

        try:
            for asset1, asset2 in self.config.arbitrage_pairs:
                if asset1 in self.price_data and asset2 in self.price_data:
                    opportunity = self._analyze_pair_arbitrage(asset1, asset2)
                    if opportunity:
                        opp_id = f"{asset1}_{asset2}_{datetime.now().timestamp()}"
                        opportunities[opp_id] = opportunity

            return opportunities

        except Exception as e:
            self._log_error("Arbitrage detection failed", e)
            return {}

    def _analyze_pair_arbitrage(self, asset1: str, asset2: str) -> Optional[Dict[str, Any]]:
        """Analyze arbitrage opportunity between two assets"""

        try:
            price1 = self.price_data[asset1]
            price2 = self.price_data[asset2]

            # Calculate price ratio
            ratio = price1 / price2 if price2 != 0 else 0

            # Get historical ratio for comparison
            historical_ratio = self._get_historical_ratio(asset1, asset2)

            if historical_ratio == 0:
                return None

            # Calculate discrepancy
            discrepancy = abs(ratio - historical_ratio) / historical_ratio

            if discrepancy > self.config.min_price_discrepancy:
                return {
                    'asset1': asset1,
                    'asset2': asset2,
                    'price1': price1,
                    'price2': price2,
                    'current_ratio': ratio,
                    'historical_ratio': historical_ratio,
                    'discrepancy': discrepancy,
                    'opportunity_type': ArbitrageType.PRICE_ARBITRAGE,
                    'timestamp': datetime.now(),
                    'confidence': min(discrepancy / self.config.min_price_discrepancy, 1.0)
                }

            return None

        except Exception as e:
            logger.error(f"Pair arbitrage analysis failed for {asset1}-{asset2}: {e}")
            return None

    def _get_historical_ratio(self, asset1: str, asset2: str) -> float:
        """Get historical price ratio between two assets"""

        try:
            if asset1 not in self.market_data or asset2 not in self.market_data:
                return 0.0

            data1 = self.market_data[asset1]
            data2 = self.market_data[asset2]

            if len(data1) < 20 or len(data2) < 20:
                return 0.0

            # Calculate average ratio over last 20 periods
            prices1 = data1['close'].tail(20)
            prices2 = data2['close'].tail(20)

            ratios = prices1 / prices2
            return ratios.mean()

        except Exception as e:
            logger.error(f"Historical ratio calculation failed for {asset1}-{asset2}: {e}")
            return 0.0

    def _validate_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Validate arbitrage opportunity"""

        try:
            # Check confidence threshold
            if opportunity.get('confidence', 0) < self.config.confidence_threshold:
                return False

            # Check timing (opportunity should be recent)
            age = (datetime.now() - opportunity['timestamp']).total_seconds()
            if age > self.config.opportunity_timeout:
                return False

            # Check transaction costs
            estimated_cost = self._estimate_transaction_cost(opportunity)
            if estimated_cost > self.config.transaction_cost_threshold:
                return False

            return True

        except Exception as e:
            logger.error(f"Opportunity validation failed: {e}")
            return False

    def _estimate_transaction_cost(self, opportunity: Dict[str, Any]) -> float:
        """Estimate transaction cost for arbitrage execution"""

        try:
            # Simplified transaction cost estimation
            # In practice, this would consider bid-ask spreads, market impact, etc.
            base_cost = 0.0002  # 0.02% base cost

            # Adjust for discrepancy size (larger discrepancies may have higher costs)
            discrepancy_adjustment = opportunity.get('discrepancy', 0) * 0.1

            return base_cost + discrepancy_adjustment

        except Exception as e:
            logger.error(f"Transaction cost estimation failed: {e}")
            return 0.001  # Conservative estimate

    def _create_arbitrage_signals(self, opportunity: Dict[str, Any]) -> List[StrategySignal]:
        """Create trading signals for arbitrage opportunity"""

        signals = []

        try:
            asset1 = opportunity['asset1']
            asset2 = opportunity['asset2']
            current_ratio = opportunity['current_ratio']
            historical_ratio = opportunity['historical_ratio']

            # Determine which asset is overvalued/undervalued
            if current_ratio > historical_ratio:
                # Asset1 is overvalued relative to Asset2
                # Sell Asset1, Buy Asset2

                signal1 = StrategySignal(
                    signal_id=f"arbitrage_signal_1_{datetime.now().timestamp()}",
                    strategy_id=self.strategy_id,
                    symbol=asset1,
                    signal_type=SignalType.SELL,
                    strength=opportunity['confidence'],
                    confidence=opportunity['confidence'],
                    target_weight=self.config.max_position_pct,  # Use as percentage weight
                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now()
                )
                signals.append(signal1)

                signal2 = StrategySignal(
                    signal_id=f"arbitrage_signal_2_{datetime.now().timestamp()}",
                    strategy_id=self.strategy_id,
                    symbol=asset2,
                    signal_type=SignalType.BUY,
                    strength=opportunity['confidence'],
                    confidence=opportunity['confidence'],
                    target_weight=self.config.max_position_pct,  # Use as percentage weight
                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now()
                )
                signals.append(signal2)

            else:
                # Asset1 is undervalued relative to Asset2
                # Buy Asset1, Sell Asset2

                signal1 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=asset1,
                    signal_type=SignalType.BUY,
                    strength=opportunity['confidence'],
                    confidence=opportunity['confidence'],
                    target_weight=self.config.max_position_pct,  # Use as percentage weight
                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'arbitrage_type': opportunity['opportunity_type'].value,
                        'pair_asset': asset2,
                        'discrepancy': opportunity['discrepancy'],
                        'expected_convergence': 'buy_undervalued'
                    }
                )
                signals.append(signal1)

                signal2 = StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=asset2,
                    signal_type=SignalType.SELL,
                    strength=opportunity['confidence'],
                    confidence=opportunity['confidence'],
                    target_weight=self.config.max_position_pct,  # Use as percentage weight
                    quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                    timestamp=datetime.now(),
                    additional_data={  # FIXED: metadata -> additional_data
                        'arbitrage_type': opportunity['opportunity_type'].value,
                        'pair_asset': asset1,
                        'discrepancy': opportunity['discrepancy'],
                        'expected_convergence': 'sell_overvalued'
                    }
                )
                signals.append(signal2)

            return signals

        except Exception as e:
            self._log_error("Arbitrage signal creation failed", e)
            return []

    # ========================================
    # HELPER METHODS
    # ========================================

    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""

        for symbol, data in market_data.items():
            self.market_data[symbol] = data

            # Update current prices
            if len(data) > 0:
                self.price_data[symbol] = data['close'].iloc[-1]

    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""

        self.market_data.clear()
        self.price_data.clear()
        self.arbitrage_opportunities.clear()
        self.executed_arbitrages.clear()
        self.missed_opportunities.clear()

    def _check_opportunity_expiration(self) -> None:
        """Check for expired arbitrage opportunities"""

        try:
            current_time = datetime.now()
            expired_opportunities = []

            for opp_id, opportunity in self.arbitrage_opportunities.items():
                age = (current_time - opportunity['timestamp']).total_seconds()
                if age > self.config.opportunity_timeout:
                    expired_opportunities.append(opp_id)
                    self.missed_opportunities.append(opportunity)

            # Remove expired opportunities
            for opp_id in expired_opportunities:
                del self.arbitrage_opportunities[opp_id]

        except Exception as e:
            self._log_error("Opportunity expiration check failed", e)

    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================

    def get_arbitrage_summary(self) -> Dict[str, Any]:
        """Get comprehensive arbitrage strategy summary"""

        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Arbitrage',
            'arbitrage_pairs': len(self.config.arbitrage_pairs),
            'active_opportunities': len(self.arbitrage_opportunities),
            'executed_arbitrages': len(self.executed_arbitrages),
            'missed_opportunities': len(self.missed_opportunities),
            'performance_summary': self.get_performance_summary(),
            'current_opportunities': {
                opp_id: {
                    'asset1': opp['asset1'],
                    'asset2': opp['asset2'],
                    'discrepancy': opp['discrepancy'],
                    'confidence': opp['confidence'],
                    'age_seconds': (datetime.now() - opp['timestamp']).total_seconds()
                }
                for opp_id, opp in self.arbitrage_opportunities.items()
            }
        }
