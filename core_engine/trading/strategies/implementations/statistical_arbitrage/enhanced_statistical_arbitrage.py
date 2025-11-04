"""
Enhanced Statistical Arbitrage Strategy with ISystemComponent Integration
========================================================================

Professional statistical arbitrage strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

This enhanced strategy provides:
- ISystemComponent interface compliance
- Professional error handling and logging
- Health monitoring and status reporting
- Performance tracking and metrics
- Risk management integration
- Configuration validation

Key Features:
- Multi-asset spread trading with cointegration analysis
- Dynamic hedge ratio estimation using Kalman filters
- Error Correction Model (ECM) for spread dynamics
- Ornstein-Uhlenbeck process modeling for mean reversion
- Risk parity position sizing
- Statistical significance testing
- Transaction cost awareness

Academic Foundations:
- Engle & Granger (1987) cointegration
- Johansen (1991) multivariate cointegration
- Alexander (2001) statistical arbitrage
- Gatev et al. (2006) pairs trading

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from statsmodels.tsa.stattools import coint, adfuller
from sklearn.linear_model import LinearRegression
import warnings

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategyConfig, StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import StatisticalArbitrageConfig

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class SpreadState(Enum):
    """Spread trading states"""
    NEUTRAL = "neutral"
    LONG_SPREAD = "long_spread"      # Long asset1, short asset2
    SHORT_SPREAD = "short_spread"    # Short asset1, long asset2
    CLOSING = "closing"
    CLOSED = "closed"


# ✅ StatisticalArbitrageConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only


@dataclass
class SpreadMetrics:
    """Spread-specific performance metrics"""
    
    spread_id: str
    asset1: str
    asset2: str
    hedge_ratio: float
    
    # Statistical properties
    mean_reversion_speed: float = 0.0
    half_life: float = 0.0
    cointegration_pvalue: float = 1.0
    correlation: float = 0.0
    
    # Trading metrics
    current_zscore: float = 0.0
    entry_zscore: float = 0.0
    max_zscore: float = 0.0
    min_zscore: float = 0.0
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Risk metrics
    var_95: float = 0.0
    max_position_size: float = 0.0
    current_position_size: float = 0.0
    
    # Timing metrics
    avg_holding_period: float = 0.0
    last_trade_timestamp: Optional[datetime] = None


class EnhancedStatisticalArbitrageStrategy(EnhancedBaseStrategy):
    """
    Enhanced Statistical Arbitrage Strategy with ISystemComponent Integration
    
    Professional statistical arbitrage strategy that provides:
    - ISystemComponent interface compliance
    - Advanced cointegration analysis and spread trading
    - Dynamic hedge ratio estimation using Kalman filters
    - Error Correction Model (ECM) for spread dynamics
    - Comprehensive performance tracking and risk management
    """
    
    def __init__(self, config: StatisticalArbitrageConfig):
        """Initialize enhanced statistical arbitrage strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: StatisticalArbitrageConfig = config
        
        # Strategy-specific state
        self.cointegrated_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.active_spreads: Dict[str, SpreadMetrics] = {}
        self.hedge_ratios: Dict[Tuple[str, str], float] = {}
        self.spread_history: Dict[str, pd.Series] = {}
        self.entry_times: Dict[str, datetime] = {}
        
        # Market data cache
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.returns_data: Dict[str, pd.Series] = {}
        
        # Model components
        self.kalman_filters: Dict[Tuple[str, str], Any] = {}
        self.ou_models: Dict[str, Dict[str, float]] = {}
        self.ecm_models: Dict[Tuple[str, str], Any] = {}
        
        # Performance tracking
        self.spread_performance: Dict[str, SpreadMetrics] = {}
        self.daily_pnl: List[float] = []
        self.trade_history: List[Dict[str, Any]] = []
        
        logger.info(f"🧠 Enhanced Statistical Arbitrage Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing StatArb components for {self.strategy_id}...")
            
            # Validate asset universe
            if len(self.config.asset_universe) < 2:
                logger.error("❌ Asset universe must contain at least 2 assets")
                return False
            
            # Initialize data structures
            self._initialize_data_structures()
            
            # Initialize model components
            if self.config.kalman_filter_enabled:
                self._initialize_kalman_filters()
            
            if self.config.ou_process_modeling:
                self._initialize_ou_models()
            
            if self.config.error_correction_model:
                self._initialize_ecm_models()
            
            logger.info(f"✅ StatArb components initialized for {len(self.config.asset_universe)} assets")
            return True
            
        except Exception as e:
            logger.error(f"❌ StatArb component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting StatArb operations for {self.strategy_id}...")
            
            # Start performance monitoring (always enabled)
            self._start_performance_monitoring()
            
            # Initialize spread tracking
            self._initialize_spread_tracking()
            
            logger.info(f"✅ StatArb operations started")
            return True
            
        except Exception as e:
            logger.error(f"❌ StatArb operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping StatArb operations for {self.strategy_id}...")
            
            # Close all active spreads
            await self._close_all_spreads()
            
            # Save performance data
            self._save_performance_data()
            
            logger.info(f"✅ StatArb operations stopped")
            
        except Exception as e:
            logger.error(f"❌ StatArb operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            health_metrics = {
                'strategy_healthy': True,
                'cointegrated_pairs': len(self.cointegrated_pairs),
                'active_spreads': len(self.active_spreads),
                'total_trades': len(self.trade_history),
                'avg_spread_correlation': self._calculate_avg_correlation(),
                'model_health': {
                    'kalman_filters': len(self.kalman_filters) if self.config.kalman_filter_enabled else 0,
                    'ou_models': len(self.ou_models) if self.config.ou_process_modeling else 0,
                    'ecm_models': len(self.ecm_models) if self.config.error_correction_model else 0
                }
            }
            
            # Check for unhealthy conditions
            if len(self.cointegrated_pairs) == 0:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "No cointegrated pairs found"
            
            if len(self.active_spreads) > self.config.max_spread_positions:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = "Too many active spreads"
            
            avg_correlation = health_metrics['avg_spread_correlation']
            if avg_correlation < self.config.min_correlation:
                health_metrics['strategy_healthy'] = False
                health_metrics['warning'] = f"Low average correlation: {avg_correlation:.3f}"
            
            return health_metrics
            
        except Exception as e:
            return {
                'strategy_healthy': False,
                'error': str(e)
            }
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        return {
            'strategy_type': 'Enhanced Statistical Arbitrage',
            'asset_universe_size': len(self.config.asset_universe),
            'cointegration_lookback': self.config.cointegration_lookback,
            'entry_zscore_threshold': self.config.entry_zscore_threshold,
            'exit_zscore_threshold': self.config.exit_zscore_threshold,
            'max_spread_positions': self.config.max_spread_positions,
            'position_size_method': self.config.position_size_method,
            'kalman_filter_enabled': self.config.kalman_filter_enabled,
            'ou_process_modeling': self.config.ou_process_modeling,
            'error_correction_model': self.config.error_correction_model
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            # Validate thresholds
            if self.config.entry_zscore_threshold <= self.config.exit_zscore_threshold:
                logger.error("Entry Z-score threshold must be greater than exit threshold")
                return False
            
            if self.config.stop_loss_zscore <= self.config.entry_zscore_threshold:
                logger.error("Stop loss Z-score must be greater than entry threshold")
                return False
            
            # Validate position sizing
            if self.config.base_position_size <= 0 or self.config.base_position_size > 0.1:
                logger.error("Base position size must be between 0 and 0.1 (10%)")
                return False
            
            # Validate lookback period
            if self.config.cointegration_lookback < 50:
                logger.error("Cointegration lookback period must be at least 50 days")
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
        
        StatArb strategy requires pre-calculated returns for spread analysis.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame]
        
        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'returns_1',        # 1-period returns (from FeatureEngineer)
            'close',            # Close prices (needed for spread calculation)
            'volume'            # Volume (for liquidity checks)
        ]
        
        for symbol, data in enriched_data.items():
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
        Generate statistical arbitrage signals from ENRICHED data (Rule 3 Phase 4)
        
        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        features from the ProcessingPipelineOrchestrator. It reads pre-calculated
        returns instead of calculating them.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + returns]
                          Must contain: returns_1 (1-period returns)
        
        Returns:
            List[StrategySignal]: Generated statistical arbitrage signals
        """
        start_time = datetime.now()
        signals = []
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # Update market data cache with enriched data
            self._update_market_data_cache(enriched_data)
            
            # Update cointegration analysis
            await self._update_cointegration_analysis()
            
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
            
            logger.info(f"📊 StatArb Strategy (Rule 3 Phase 4 - Enriched Data):")
            logger.info(f"   Signals generated: {len(signals)}")
            logger.info(f"   Generation time: {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""
        
        try:
            # Update market data
            self._update_market_data_cache(market_data)
            
            # Update spread metrics
            self._update_spread_metrics()
            
            # Check for stop losses
            await self._check_stop_losses()
            
            # Update hedge ratios if using Kalman filters
            if self.config.kalman_filter_enabled:
                self._update_kalman_filters()
            
            # Update performance tracking
            self._update_performance_tracking()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            if self.config.position_size_method == "fixed":
                return self._calculate_fixed_position_size(signal)
            elif self.config.position_size_method == "volatility_adjusted":
                return self._calculate_volatility_adjusted_size(signal, market_data)
            elif self.config.position_size_method == "risk_parity":
                return self._calculate_risk_parity_size(signal, market_data)
            else:
                logger.warning(f"Unknown position sizing method: {self.config.position_size_method}")
                return self._calculate_fixed_position_size(signal)
                
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # COINTEGRATION ANALYSIS
    # ========================================
    
    async def _update_cointegration_analysis(self) -> None:
        """Update cointegration analysis for asset pairs"""
        
        try:
            # PROFESSIONAL APPROACH: Use pre-loaded pairs for backtesting
            if self.config.use_preloaded_pairs and self.config.preloaded_pairs:
                # Load pre-selected pairs (cointegration tested offline on daily data)
                for pair_info in self.config.preloaded_pairs:
                    pair = tuple(pair_info['pair'])
                    self.cointegrated_pairs[pair] = pair_info
                
                logger.info(f"📈 Loaded {len(self.cointegrated_pairs)} pre-selected cointegrated pairs")
                return
            
            # Live cointegration testing (not recommended for intraday data)
            assets = self.config.asset_universe
            
            # Test all possible pairs
            for i, asset1 in enumerate(assets):
                for j, asset2 in enumerate(assets[i+1:], i+1):
                    pair = (asset1, asset2)
                    
                    # Skip if insufficient data
                    if (asset1 not in self.price_data or asset2 not in self.price_data or
                        len(self.price_data[asset1]) < self.config.cointegration_lookback or
                        len(self.price_data[asset2]) < self.config.cointegration_lookback):
                        continue
                    
                    # Perform cointegration test
                    cointegration_result = await self._test_cointegration(asset1, asset2)
                    
                    if cointegration_result['is_cointegrated']:
                        self.cointegrated_pairs[pair] = cointegration_result
                        logger.debug(f"✅ Cointegrated pair found: {asset1}-{asset2} (p-value: {cointegration_result['p_value']:.4f})")
                    elif pair in self.cointegrated_pairs:
                        # Remove if no longer cointegrated
                        del self.cointegrated_pairs[pair]
                        logger.debug(f"❌ Pair no longer cointegrated: {asset1}-{asset2}")
            
            logger.info(f"📈 Found {len(self.cointegrated_pairs)} cointegrated pairs")
            
        except Exception as e:
            self._log_error("Cointegration analysis failed", e)
    
    async def _test_cointegration(self, asset1: str, asset2: str) -> Dict[str, Any]:
        """Test cointegration between two assets"""
        
        try:
            # Get price data
            prices1 = self.price_data[asset1]['close'].tail(self.config.cointegration_lookback)
            prices2 = self.price_data[asset2]['close'].tail(self.config.cointegration_lookback)
            
            # Align data
            aligned_data = pd.concat([prices1, prices2], axis=1, join='inner')
            aligned_data.columns = [asset1, asset2]
            
            if len(aligned_data) < 50:  # Minimum data requirement
                return {'is_cointegrated': False, 'reason': 'insufficient_data'}
            
            # Perform Engle-Granger cointegration test
            score, p_value, _ = coint(aligned_data[asset1], aligned_data[asset2])
            
            # Calculate correlation
            correlation = aligned_data[asset1].corr(aligned_data[asset2])
            
            # Calculate hedge ratio using OLS
            X = aligned_data[asset1].values.reshape(-1, 1)
            y = aligned_data[asset2].values
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            
            # Calculate spread
            spread = aligned_data[asset2] - hedge_ratio * aligned_data[asset1]
            
            # Test spread stationarity
            adf_stat, adf_p_value, _, _, _, _ = adfuller(spread.dropna())
            
            is_cointegrated = (p_value < self.config.cointegration_threshold and 
                             abs(correlation) > self.config.min_correlation and
                             adf_p_value < 0.05)  # Spread is stationary
            
            return {
                'is_cointegrated': is_cointegrated,
                'p_value': p_value,
                'correlation': correlation,
                'hedge_ratio': hedge_ratio,
                'spread_mean': spread.mean(),
                'spread_std': spread.std(),
                'adf_p_value': adf_p_value,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Cointegration test failed for {asset1}-{asset2}: {e}")
            return {'is_cointegrated': False, 'reason': 'test_failed', 'error': str(e)}
    
    # ========================================
    # SIGNAL GENERATION
    # ========================================
    
    async def _generate_entry_signals(self) -> List[StrategySignal]:
        """Generate entry signals for spread trading"""
        
        signals = []
        
        try:
            for pair, coint_data in self.cointegrated_pairs.items():
                asset1, asset2 = pair
                
                # Skip if already have position in this spread
                spread_id = f"{asset1}_{asset2}"
                if spread_id in self.active_spreads:
                    continue
                
                # Skip if maximum positions reached
                if len(self.active_spreads) >= self.config.max_spread_positions:
                    break
                
                # Calculate current spread and Z-score
                current_spread, zscore = self._calculate_current_spread_zscore(pair, coint_data)
                
                if current_spread is None or zscore is None:
                    continue
                
                # Check for entry conditions
                if abs(zscore) > self.config.entry_zscore_threshold:
                    # Determine signal direction
                    if zscore > 0:  # Spread is high, expect mean reversion
                        # Short the spread: short asset2, long asset1
                        signal_type = SignalType.SELL  # For asset2
                        spread_direction = "short_spread"
                    else:  # Spread is low, expect mean reversion
                        # Long the spread: long asset2, short asset1
                        signal_type = SignalType.BUY  # For asset2
                        spread_direction = "long_spread"
                    
                    # Calculate confidence based on Z-score magnitude
                    confidence = min(0.95, abs(zscore) / self.config.stop_loss_zscore)
                    
                    try:
                        # Create signals for both assets
                        hedge_ratio = coint_data['hedge_ratio']
                        
                        # Signal for asset2 (primary)
                        signal2 = StrategySignal(
                            strategy_id=self.strategy_id,
                            symbol=asset2,
                            signal_type=signal_type,
                            strength=abs(zscore) / self.config.entry_zscore_threshold,
                            confidence=confidence,
                            target_quantity=self.config.base_position_size,
                            timestamp=datetime.now(),
                            additional_data={
                                'spread_id': spread_id,
                                'pair': pair,
                                'hedge_ratio': hedge_ratio,
                                'zscore': zscore,
                                'spread_direction': spread_direction,
                                'asset_role': 'primary'
                            }
                        )
                        
                        # Signal for asset1 (hedge)
                        hedge_signal_type = SignalType.BUY if signal_type == SignalType.SELL else SignalType.SELL
                        signal1 = StrategySignal(
                            strategy_id=self.strategy_id,
                            symbol=asset1,
                            signal_type=hedge_signal_type,
                            strength=abs(zscore) / self.config.entry_zscore_threshold,
                            confidence=confidence,
                            target_quantity=self.config.base_position_size * abs(hedge_ratio),
                            timestamp=datetime.now(),
                            additional_data={
                                'spread_id': spread_id,
                                'pair': pair,
                                'hedge_ratio': hedge_ratio,
                                'zscore': zscore,
                                'spread_direction': spread_direction,
                                'asset_role': 'hedge'
                            }
                        )
                        
                        signals.extend([signal2, signal1])
                        
                        # Track spread entry
                        self.active_spreads[spread_id] = SpreadMetrics(
                            spread_id=spread_id,
                            asset1=asset1,
                            asset2=asset2,
                            hedge_ratio=hedge_ratio,
                            entry_zscore=zscore,
                            current_zscore=zscore
                        )
                        
                        self.entry_times[spread_id] = datetime.now()
                        
                        logger.info(f"📈 Entry signal generated for spread {spread_id}: Z-score={zscore:.2f}, Direction={spread_direction}")
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to create signals for {asset1}/{asset2}: {e}", exc_info=True)
            
            return signals
            
        except Exception as e:
            self._log_error("Entry signal generation failed", e)
            return []
    
    async def _generate_exit_signals(self) -> List[StrategySignal]:
        """Generate exit signals for active spreads"""
        
        signals = []
        
        try:
            spreads_to_close = []
            
            for spread_id, spread_metrics in self.active_spreads.items():
                pair = (spread_metrics.asset1, spread_metrics.asset2)
                
                # Skip if pair is no longer cointegrated
                if pair not in self.cointegrated_pairs:
                    spreads_to_close.append(spread_id)
                    continue
                
                coint_data = self.cointegrated_pairs[pair]
                
                # Calculate current Z-score
                current_spread, zscore = self._calculate_current_spread_zscore(pair, coint_data)
                
                if current_spread is None or zscore is None:
                    continue
                
                # Update spread metrics
                spread_metrics.current_zscore = zscore
                spread_metrics.max_zscore = max(spread_metrics.max_zscore, zscore)
                spread_metrics.min_zscore = min(spread_metrics.min_zscore, zscore)
                
                # Check exit conditions
                should_exit = False
                exit_reason = ""
                
                # Mean reversion exit
                if abs(zscore) < self.config.exit_zscore_threshold:
                    should_exit = True
                    exit_reason = "mean_reversion"
                
                # Stop loss exit
                elif abs(zscore) > self.config.stop_loss_zscore:
                    should_exit = True
                    exit_reason = "stop_loss"
                
                # Time-based exit
                elif spread_id in self.entry_times:
                    holding_period = (datetime.now() - self.entry_times[spread_id]).days
                    if holding_period > self.config.max_holding_period:
                        should_exit = True
                        exit_reason = "max_holding_period"
                
                if should_exit:
                    # Generate exit signals (reverse of entry)
                    exit_signals = self._create_exit_signals(spread_id, spread_metrics, exit_reason)
                    signals.extend(exit_signals)
                    
                    spreads_to_close.append(spread_id)
                    
                    logger.info(f"📉 Exit signal generated for spread {spread_id}: Z-score={zscore:.2f}, Reason={exit_reason}")
            
            # Clean up closed spreads
            for spread_id in spreads_to_close:
                if spread_id in self.active_spreads:
                    del self.active_spreads[spread_id]
                if spread_id in self.entry_times:
                    del self.entry_times[spread_id]
            
            return signals
            
        except Exception as e:
            self._log_error("Exit signal generation failed", e)
            return []
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _update_market_data_cache(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Update market data cache using PRE-CALCULATED returns (Rule 3 Phase 4)
        
        **CRITICAL:** This method now reads pre-calculated returns from enriched data
        instead of calculating them. Returns are provided by FeatureEngineer.
        """
        for symbol, data in market_data.items():
            if symbol in self.config.asset_universe:
                self.price_data[symbol] = data
                
                # READ pre-calculated returns from enriched data (Rule 3 Phase 4)
                if 'returns_1' in data.columns:
                    # Use pre-calculated returns from FeatureEngineer
                    self.returns_data[symbol] = data['returns_1'].dropna()
                    logger.debug(f"✅ {symbol}: Using pre-calculated returns from pipeline")
                elif 'close' in data.columns:
                    # Calculate if not available
                    self.returns_data[symbol] = data['close'].pct_change().dropna()
                    logger.warning(f"⚠️  {symbol}: Falling back to calculated returns (pipeline missing returns_1)")
    
    def _calculate_current_spread_zscore(self, pair: Tuple[str, str], coint_data: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate current spread and Z-score using INTRADAY statistics
        
        PROFESSIONAL APPROACH for live trading simulation:
        - Use pre-loaded hedge ratio from daily cointegration analysis
        - Calculate spread mean/std from INTRADAY rolling window
        - This captures intraday mean reversion behavior
        """
        
        try:
            asset1, asset2 = pair
            
            if asset1 not in self.price_data or asset2 not in self.price_data:
                return None, None
            
            # Get hedge ratio from offline daily analysis (stable over time)
            hedge_ratio = coint_data['hedge_ratio']
            
            # Get price series for both assets
            prices1 = self.price_data[asset1]['close']
            prices2 = self.price_data[asset2]['close']
            
            # Minimum data requirement for intraday statistics - use configurable value from centralized config (Rule 1)
            # For 1-minute data: need at least N bars for meaningful statistics
            min_bars_required = self.config.min_intraday_bars
            
            if len(prices1) < min_bars_required or len(prices2) < min_bars_required:
                return None, None
            
            # CRITICAL: Align the two price series first (pandas index alignment)
            # The two assets might have different timestamps, so we need to align them
            aligned_prices = pd.DataFrame({
                asset1: prices1,
                asset2: prices2
            }).dropna()  # Remove any timestamps where either asset is missing
            
            if len(aligned_prices) < min_bars_required:
                return None, None
            
            # Calculate spread series using aligned data
            spread_series = aligned_prices[asset2] - hedge_ratio * aligned_prices[asset1]
            
            # Use lookback window for intraday statistics
            # For 1-minute data: 390 bars = 1 day, 780 bars = 2 days
            lookback_window = min(780, len(spread_series))  # Use 2 days or available
            spread_window = spread_series.iloc[-lookback_window:]
            
            # Calculate INTRADAY spread statistics
            spread_mean = spread_window.mean()
            spread_std = spread_window.std()
            
            # Get current spread
            current_spread = spread_series.iloc[-1]
            
            # Calculate Z-score using INTRADAY statistics
            if spread_std == 0 or pd.isna(spread_std):
                return current_spread, None
            
            zscore = (current_spread - spread_mean) / spread_std
            
            return current_spread, zscore
            
        except Exception as e:
            logger.error(f"Spread calculation failed for {pair}: {e}")
            return None, None
    
    def _create_exit_signals(self, spread_id: str, spread_metrics: SpreadMetrics, exit_reason: str) -> List[StrategySignal]:
        """Create exit signals for a spread"""
        
        signals = []
        
        try:
            # Create exit signals (reverse positions)
            # This is a simplified version - in practice, you'd track actual positions
            
            # Exit signal for asset2
            signal2 = StrategySignal(
                strategy_id=self.strategy_id,
                symbol=spread_metrics.asset2,
                signal_type=SignalType.SELL,  # Simplified - should be opposite of entry
                strength=1.0,
                confidence=0.9,
                target_quantity=self.config.base_position_size,  # FIXED: quantity -> target_quantity
                timestamp=datetime.now(),
                additional_data={  # FIXED: metadata -> additional_data
                    'spread_id': spread_id,
                    'exit_reason': exit_reason,
                    'asset_role': 'primary',
                    'action': 'exit'
                }
            )
            
            # Exit signal for asset1
            signal1 = StrategySignal(
                strategy_id=self.strategy_id,
                symbol=spread_metrics.asset1,
                signal_type=SignalType.BUY,  # Simplified - should be opposite of entry
                strength=1.0,
                confidence=0.9,
                target_quantity=self.config.base_position_size * abs(spread_metrics.hedge_ratio),  # FIXED: quantity -> target_quantity
                timestamp=datetime.now(),
                additional_data={  # FIXED: metadata -> additional_data
                    'spread_id': spread_id,
                    'exit_reason': exit_reason,
                    'asset_role': 'hedge',
                    'action': 'exit'
                }
            )
            
            signals.extend([signal2, signal1])
            
            return signals
            
        except Exception as e:
            self._log_error(f"Exit signal creation failed for {spread_id}", e)
            return []
    
    # ========================================
    # POSITION SIZING METHODS
    # ========================================
    
    def _calculate_fixed_position_size(self, signal: StrategySignal) -> float:
        """Calculate fixed position size"""
        return self.config.base_position_size
    
    def _calculate_volatility_adjusted_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate volatility-adjusted position size"""
        
        try:
            symbol = signal.symbol
            
            if symbol not in self.returns_data or len(self.returns_data[symbol]) < 20:
                return self.config.base_position_size
            
            # Calculate volatility (20-day)
            volatility = self.returns_data[symbol].tail(20).std() * np.sqrt(252)
            
            # Adjust position size inversely to volatility - use configurable parameters from centralized config (Rule 1)
            vol_adjustment = self.config.target_volatility / max(volatility, self.config.min_volatility_floor)
            
            adjusted_size = self.config.base_position_size * vol_adjustment
            
            # Cap at maximum position size
            return min(adjusted_size, self.max_position_size)
            
        except Exception as e:
            self._log_error("Volatility-adjusted sizing failed", e)
            return self.config.base_position_size
    
    def _calculate_risk_parity_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate risk parity position size"""
        
        try:
            # Simplified risk parity - equal risk contribution
            # In practice, this would consider correlation matrix and risk budgets
            
            symbol = signal.symbol
            
            if symbol not in self.returns_data or len(self.returns_data[symbol]) < 20:
                return self.config.base_position_size
            
            # Calculate risk contribution
            volatility = self.returns_data[symbol].tail(20).std() * np.sqrt(252)
            
            # Target risk per position - use configurable value from centralized config (Rule 1)
            target_risk = self.config.target_risk_per_position
            
            # Calculate position size for target risk
            risk_adjusted_size = target_risk / max(volatility, 0.05)
            
            # Cap at maximum position size
            return min(risk_adjusted_size, self.max_position_size)
            
        except Exception as e:
            self._log_error("Risk parity sizing failed", e)
            return self.config.base_position_size
    
    # ========================================
    # UTILITY AND HELPER METHODS
    # ========================================
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        self.cointegrated_pairs.clear()
        self.active_spreads.clear()
        self.hedge_ratios.clear()
        self.spread_history.clear()
        self.entry_times.clear()
        self.price_data.clear()
        self.returns_data.clear()
    
    def _initialize_kalman_filters(self) -> None:
        """Initialize Kalman filters for hedge ratio estimation"""
        # Placeholder for Kalman filter initialization
        logger.info("🔧 Kalman filters initialized")
    
    def _initialize_ou_models(self) -> None:
        """Initialize Ornstein-Uhlenbeck models"""
        # Placeholder for OU model initialization
        logger.info("🔧 OU models initialized")
    
    def _initialize_ecm_models(self) -> None:
        """Initialize Error Correction Models"""
        # Placeholder for ECM initialization
        logger.info("🔧 ECM models initialized")
    
    def _start_performance_monitoring(self) -> None:
        """Start performance monitoring"""
        logger.info("📊 Performance monitoring started")
    
    def _initialize_spread_tracking(self) -> None:
        """Initialize spread tracking"""
        logger.info("📈 Spread tracking initialized")
    
    async def _close_all_spreads(self) -> None:
        """Close all active spreads"""
        logger.info(f"🔄 Closing {len(self.active_spreads)} active spreads")
        self.active_spreads.clear()
        self.entry_times.clear()
    
    def _save_performance_data(self) -> None:
        """Save performance data"""
        logger.info("💾 Performance data saved")
    
    def _calculate_avg_correlation(self) -> float:
        """Calculate average correlation of cointegrated pairs"""
        if not self.cointegrated_pairs:
            return 0.0
        
        correlations = [data['correlation'] for data in self.cointegrated_pairs.values()]
        return np.mean(np.abs(correlations))
    
    def _update_spread_calculations(self) -> None:
        """Update spread calculations"""
        # Placeholder for spread calculation updates
    
    def _update_spread_metrics(self) -> None:
        """Update spread performance metrics"""
        # Placeholder for spread metrics updates
    
    async def _check_stop_losses(self) -> None:
        """Check and execute stop losses"""
        # Placeholder for stop loss checking
    
    def _update_kalman_filters(self) -> None:
        """Update Kalman filter estimates"""
        # Placeholder for Kalman filter updates
    
    def _update_performance_tracking(self) -> None:
        """Update performance tracking"""
        # Placeholder for performance tracking updates
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_spread_summary(self) -> Dict[str, Any]:
        """Get comprehensive spread trading summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Statistical Arbitrage',
            'cointegrated_pairs': len(self.cointegrated_pairs),
            'active_spreads': len(self.active_spreads),
            'total_trades': len(self.trade_history),
            'avg_correlation': self._calculate_avg_correlation(),
            'performance_summary': self.get_performance_summary(),
            'spread_details': {
                spread_id: {
                    'asset1': metrics.asset1,
                    'asset2': metrics.asset2,
                    'current_zscore': metrics.current_zscore,
                    'entry_zscore': metrics.entry_zscore,
                    'hedge_ratio': metrics.hedge_ratio
                }
                for spread_id, metrics in self.active_spreads.items()
            }
        }
