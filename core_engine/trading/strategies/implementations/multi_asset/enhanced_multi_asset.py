"""
Enhanced Multi-Asset Strategy with ISystemComponent Integration
=============================================================

Professional multi-asset strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

Key Features:
- Cross-asset correlation analysis
- Portfolio-level optimization
- Risk budgeting across assets
- Dynamic asset allocation
- Professional portfolio management

Author: StatArb_Gemini Architecture Compliance
Version: 1.0.0 (Phase 2.3 Enhancement)
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategyConfig, StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
# REQUIRED: Use centralized config only - no local fallback definitions per Rule 1
from core_engine.config import MultiAssetConfig

logger = logging.getLogger(__name__)

# ✅ MultiAssetConfig imported from core_engine.config (Rule 1 Section 7)
# No local config definitions - centralized configuration only


class EnhancedMultiAssetStrategy(EnhancedBaseStrategy):
    """Enhanced Multi-Asset Strategy with ISystemComponent Integration"""
    
    def __init__(self, config: MultiAssetConfig):
        """Initialize enhanced multi-asset strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: MultiAssetConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.current_weights: Dict[str, float] = {}
        self.target_weights: Dict[str, float] = {}
        # DEPRECATED: active_positions is deprecated. Use PositionBook (SSOT) instead.
        # Position tracking should be handled by Risk Manager, not strategies.
        self.active_positions: Dict[str, Dict[str, Any]] = {}  # DEPRECATED
        
        # Portfolio metrics
        self.portfolio_returns: List[float] = []
        self.portfolio_volatility: float = 0.0
        
        logger.info(f"🧠 Enhanced Multi-Asset Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Multi-Asset components for {self.strategy_id}...")
            
            if not self.config.asset_classes:
                logger.error("❌ No asset classes configured for multi-asset strategy")
                return False
            
            self._initialize_data_structures()
            self._initialize_equal_weights()
            
            all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
            logger.info(f"✅ Multi-Asset components initialized for {len(all_symbols)} symbols across {len(self.config.asset_classes)} asset classes")
            return True
            
        except Exception as e:
            logger.error(f"❌ Multi-Asset component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Multi-Asset operations for {self.strategy_id}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Multi-Asset operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Multi-Asset operations for {self.strategy_id}...")
            await self._close_all_positions()
            logger.info(f"✅ Multi-Asset operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Multi-Asset operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
            
            return {
                'strategy_healthy': True,
                'asset_classes': len(self.config.asset_classes),
                'total_symbols': len(all_symbols),
                'active_positions': len(self.active_positions),
                'portfolio_volatility': self.portfolio_volatility,
                'correlation_matrix_available': self.correlation_matrix is not None
            }
            
        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
        
        return {
            'strategy_type': 'Enhanced Multi-Asset',
            'asset_classes_count': len(self.config.asset_classes),
            'total_symbols': len(all_symbols),
            'rebalance_frequency': self.config.rebalance_frequency,
            'portfolio_vol_target': self.config.portfolio_vol_target,
            'max_asset_weight': self.config.max_asset_weight
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            if self.config.max_asset_weight <= self.config.min_asset_weight:
                logger.error("Maximum asset weight must be greater than minimum asset weight")
                return False
            
            if self.config.portfolio_vol_target <= 0:
                logger.error("Portfolio volatility target must be positive")
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
        
        Multi-asset strategy requires returns and volatility for portfolio optimization.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame]
        
        Raises:
            ValueError: If data is missing required features
        """
        required_features = [
            'returns_1',        # Pre-calculated returns
            'volatility',       # Pre-calculated volatility
            'close',            # Close prices
            'volume'            # Volume
        ]
        
        # Iterate over enriched_data keys instead of self.config.symbols
        # (MultiAssetConfig manages asset classes internally)
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
        Generate multi-asset portfolio signals from ENRICHED data (Rule 3 Phase 4)
        
        **CRITICAL CHANGE:** This method now receives enriched data with pre-calculated
        features from the ProcessingPipelineOrchestrator. It reads pre-calculated
        returns and volatility instead of calculating them.
        
        Args:
            enriched_data: Dict[symbol, enriched DataFrame with OHLCV + indicators + features]
                          Must contain: returns_1, volatility
        
        Returns:
            List[StrategySignal]: Generated multi-asset portfolio signals
        """
        start_time = datetime.now()
        signals = []
        
        try:
            # PHASE 4: Validate enriched data (Rule 3)
            self._validate_enriched_data(enriched_data)
            
            # Update market data
            self._update_market_data(enriched_data)
            
            # Calculate correlation matrix
            self._calculate_correlation_matrix()
            
            # Optimize portfolio weights
            self._optimize_portfolio_weights()
            
            # Generate rebalancing signals
            signals = await self._generate_rebalancing_signals()
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Generated {len(signals)} Multi-Asset signals in {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""
        
        try:
            self._update_market_data(market_data)
            self._update_portfolio_metrics()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            symbol = signal.symbol
            target_weight = self.target_weights.get(symbol, 0.0)
            return target_weight
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # PORTFOLIO OPTIMIZATION METHODS
    # ========================================
    
    def _calculate_correlation_matrix(self) -> None:
        """Calculate correlation matrix for all assets"""
        
        try:
            all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
            
            # Collect returns data (READ from enriched data - Rule 3 Phase 4)
            returns_data = {}
            
            for symbol in all_symbols:
                if symbol in self.market_data and len(self.market_data[symbol]) >= self.config.correlation_lookback:
                    # READ pre-calculated returns (Rule 3 Phase 4)
                    if 'returns_1' in self.market_data[symbol].columns:
                        # ✅ READ from FeatureEngineer
                        returns = self.market_data[symbol]['returns_1'].dropna()
                        logger.debug(f"✅ {symbol}: Using pre-calculated returns for correlation")
                    else:
                        # Use pre-calculated returns
                        returns = self.market_data[symbol]['close'].pct_change().dropna()
                        logger.warning(f"⚠️  {symbol}: Falling back to calculated returns for correlation")
                    
                    if len(returns) >= self.config.correlation_lookback:
                        returns_data[symbol] = returns.tail(self.config.correlation_lookback)
            
            if len(returns_data) >= 2:
                # Create DataFrame and calculate correlations
                df = pd.DataFrame(returns_data)
                self.correlation_matrix = df.corr()
            
        except Exception as e:
            logger.error(f"Correlation matrix calculation failed: {e}")
    
    def _optimize_portfolio_weights(self) -> None:
        """Optimize portfolio weights based on risk and correlation"""
        
        try:
            all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
            
            if self.config.equal_weight_baseline:
                # Start with equal weights
                equal_weight = 1.0 / len(all_symbols)
                base_weights = {symbol: equal_weight for symbol in all_symbols}
            else:
                base_weights = self.current_weights.copy()
            
            # Apply correlation-based adjustments
            optimized_weights = self._apply_correlation_adjustments(base_weights)
            
            # Apply risk budgeting
            risk_adjusted_weights = self._apply_risk_budgeting(optimized_weights)
            
            # Normalize weights
            total_weight = sum(risk_adjusted_weights.values())
            if total_weight > 0:
                self.target_weights = {
                    symbol: weight / total_weight 
                    for symbol, weight in risk_adjusted_weights.items()
                }
            else:
                self.target_weights = base_weights
            
            # Apply weight constraints
            self._apply_weight_constraints()
            
        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}")
    
    def _apply_correlation_adjustments(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """Apply correlation-based weight adjustments"""
        
        try:
            if self.correlation_matrix is None:
                return base_weights
            
            adjusted_weights = base_weights.copy()
            
            # Reduce weights for highly correlated assets
            for symbol in adjusted_weights:
                if symbol in self.correlation_matrix.index:
                    # Calculate average correlation with other assets
                    correlations = self.correlation_matrix.loc[symbol].drop(symbol)
                    avg_correlation = abs(correlations).mean()
                    
                    # Reduce weight if highly correlated
                    if avg_correlation > self.config.max_correlation:
                        correlation_penalty = avg_correlation / self.config.max_correlation
                        adjusted_weights[symbol] *= (1.0 / correlation_penalty)
            
            return adjusted_weights
            
        except Exception as e:
            logger.error(f"Correlation adjustment failed: {e}")
            return base_weights
    
    def _apply_risk_budgeting(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply risk budgeting to portfolio weights"""
        
        try:
            risk_adjusted_weights = weights.copy()
            
            # Calculate individual asset volatilities (READ from enriched data - Rule 3 Phase 4)
            asset_volatilities = {}
            
            for symbol in weights:
                if symbol in self.market_data:
                    # READ pre-calculated volatility or returns (Rule 3 Phase 4)
                    if 'volatility' in self.market_data[symbol].columns:
                        # ✅ READ pre-calculated volatility from FeatureEngineer
                        volatility = self.market_data[symbol]['volatility'].tail(20).mean()
                        asset_volatilities[symbol] = volatility
                        logger.debug(f"✅ {symbol}: Using pre-calculated volatility for risk budgeting")
                    elif 'returns_1' in self.market_data[symbol].columns:
                        # Use pre-calculated returns
                        returns = self.market_data[symbol]['returns_1'].dropna()
                        if len(returns) >= 20:
                            volatility = returns.tail(20).std() * np.sqrt(252)
                            asset_volatilities[symbol] = volatility
                        logger.warning(f"⚠️  {symbol}: Falling back to returns-based volatility for risk budgeting")
                    else:
                        # Calculate from close prices
                        returns = self.market_data[symbol]['close'].pct_change().dropna()
                        if len(returns) >= 20:
                            volatility = returns.tail(20).std() * np.sqrt(252)
                            asset_volatilities[symbol] = volatility
                        logger.warning(f"⚠️  {symbol}: Falling back to calculated volatility for risk budgeting")
            
            # Adjust weights inversely to volatility (risk parity approach)
            if asset_volatilities:
                for symbol in risk_adjusted_weights:
                    if symbol in asset_volatilities:
                        vol = asset_volatilities[symbol]
                        if vol > 0:
                            # Inverse volatility weighting
                            risk_adjusted_weights[symbol] *= (1.0 / vol)
            
            return risk_adjusted_weights
            
        except Exception as e:
            logger.error(f"Risk budgeting failed: {e}")
            return weights
    
    def _apply_weight_constraints(self) -> None:
        """Apply minimum and maximum weight constraints"""
        
        try:
            # Apply maximum weight constraint first
            for symbol in self.target_weights:
                if self.target_weights[symbol] > self.config.max_asset_weight:
                    self.target_weights[symbol] = self.config.max_asset_weight
            
            # Iteratively apply minimum weight constraint and renormalize
            # This ensures all weights meet minimum after renormalization
            max_iterations = 10
            for _ in range(max_iterations):
                # Check if all weights meet minimum constraint
                min_violations = [
                    symbol for symbol, weight in self.target_weights.items() 
                    if weight < self.config.min_asset_weight
                ]
                
                if not min_violations:
                    break  # All constraints satisfied
                
                # Apply minimum weight to violations
                for symbol in min_violations:
                    self.target_weights[symbol] = self.config.min_asset_weight
                
                # Renormalize the remaining weights
                total_weight = sum(self.target_weights.values())
                excess_weight = total_weight - 1.0
                
                if excess_weight > 0:
                    # Reduce weights proportionally for assets above minimum
                    adjustable_symbols = [
                        symbol for symbol, weight in self.target_weights.items()
                        if weight > self.config.min_asset_weight
                    ]
                    
                    if adjustable_symbols:
                        # Distribute excess weight reduction proportionally
                        total_adjustable = sum(self.target_weights[s] for s in adjustable_symbols)
                        reduction_factor = excess_weight / total_adjustable
                        
                        for symbol in adjustable_symbols:
                            self.target_weights[symbol] *= (1.0 - reduction_factor)
            
        except Exception as e:
            logger.error(f"Weight constraint application failed: {e}")
    
    async def _generate_rebalancing_signals(self) -> List[StrategySignal]:
        """Generate rebalancing signals based on target weights"""
        
        signals = []
        
        try:
            # Create a copy of current weights to avoid modifying during iteration
            current_weights_copy = self.current_weights.copy()
            
            for symbol, target_weight in self.target_weights.items():
                current_weight = current_weights_copy.get(symbol, 0.0)
                weight_diff = target_weight - current_weight
                
                # Generate signal if significant weight difference
                if abs(weight_diff) > 0.01:  # 1% threshold
                    
                    signal_type = SignalType.BUY if weight_diff > 0 else SignalType.SELL
                    
                    signal = StrategySignal(
                        strategy_id=self.strategy_id,
                        symbol=symbol,
                        signal_type=signal_type,
                        strength=min(abs(weight_diff) * 10, 1.0),
                        confidence=0.8,
                        target_weight=abs(weight_diff),  # Use as percentage weight
                        quantity_type="PERCENTAGE",  # CRITICAL FIX: Explicit quantity_type
                        timestamp=datetime.now(),
                        signal_reason='portfolio_rebalancing',
                        additional_data={
                            'current_weight': current_weight,
                            'target_weight': target_weight,
                            'weight_difference': weight_diff
                        }
                    )
                    signals.append(signal)
                    
                    # Update current weights (assuming signal will be executed)
                    self.current_weights[symbol] = target_weight
            
            return signals
            
        except Exception as e:
            self._log_error("Rebalancing signal generation failed", e)
            return []
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _update_market_data(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update market data cache"""
        
        all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
        
        for symbol, data in market_data.items():
            if symbol in all_symbols:
                self.market_data[symbol] = data
    
    def _initialize_data_structures(self) -> None:
        """Initialize strategy data structures"""
        
        self.market_data.clear()
        self.current_weights.clear()
        self.target_weights.clear()
        self.active_positions.clear()
        self.portfolio_returns.clear()
    
    def _initialize_equal_weights(self) -> None:
        """Initialize equal weights for all assets"""
        
        all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
        
        if all_symbols:
            equal_weight = 1.0 / len(all_symbols)
            self.current_weights = {symbol: equal_weight for symbol in all_symbols}
            self.target_weights = self.current_weights.copy()
    
    def _update_portfolio_metrics(self) -> None:
        """Update portfolio-level metrics"""
        
        try:
            # Calculate portfolio returns
            if self.market_data and self.current_weights:
                portfolio_return = 0.0
                
                for symbol, weight in self.current_weights.items():
                    if symbol in self.market_data and len(self.market_data[symbol]) >= 2:
                        asset_return = self.market_data[symbol]['close'].pct_change().iloc[-1]
                        if not np.isnan(asset_return):
                            portfolio_return += weight * asset_return
                
                self.portfolio_returns.append(portfolio_return)
                
                # Calculate portfolio volatility
                if len(self.portfolio_returns) >= 20:
                    self.portfolio_volatility = np.std(self.portfolio_returns[-20:]) * np.sqrt(252)
            
        except Exception as e:
            logger.error(f"Portfolio metrics update failed: {e}")
    
    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
        self.current_weights.clear()
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_multi_asset_summary(self) -> Dict[str, Any]:
        """Get comprehensive multi-asset strategy summary"""
        
        all_symbols = [symbol for symbols in self.config.asset_classes.values() for symbol in symbols]
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Multi-Asset',
            'asset_classes': len(self.config.asset_classes),
            'total_symbols': len(all_symbols),
            'active_positions': len(self.active_positions),
            'portfolio_volatility': self.portfolio_volatility,
            'performance_summary': self.get_performance_summary(),
            'current_weights': self.current_weights,
            'target_weights': self.target_weights,
            'asset_class_breakdown': {
                class_name: {
                    'symbols': symbols,
                    'total_weight': sum(self.current_weights.get(symbol, 0) for symbol in symbols)
                }
                for class_name, symbols in self.config.asset_classes.items()
            }
        }
