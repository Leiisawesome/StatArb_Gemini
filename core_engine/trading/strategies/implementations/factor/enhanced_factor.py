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
from dataclasses import dataclass, field
import logging

# Import enhanced base strategy
from ...base_strategy_enhanced import EnhancedBaseStrategy
from ...strategy_engine import (
    StrategyConfig, StrategySignal, SignalType
)

# Import centralized configuration (Rule 1 Section 7 - Configuration Management)
try:
    from core_engine.config import FactorConfig
except ImportError:
    # Fallback: local config will be used if centralized not available
    pass

logger = logging.getLogger(__name__)


@dataclass
class FactorConfig(StrategyConfig):
    """Enhanced Factor Configuration"""
    
    # Factor parameters
    factors: List[str] = field(default_factory=lambda: ['momentum', 'value', 'quality', 'volatility'])
    rebalance_frequency: int = 20           # Rebalance every 20 days
    factor_lookback: int = 60               # Factor calculation lookback
    
    # Position sizing
    base_position_pct: float = 0.02         # Base position size (2%)
    max_position_pct: float = 0.06          # Maximum position size (6%)
    
    # Asset universe
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])


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
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        
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
    
    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Generate factor-based signals"""
        
        start_time = datetime.now()
        signals = []
        
        try:
            # Update market data
            self._update_market_data(market_data)
            
            # Calculate factor scores
            self._calculate_factor_scores()
            
            # Generate signals based on factor rankings
            signals = await self._generate_factor_signals()
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Generated {len(signals)} Factor signals in {generation_time:.3f}s")
            
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
        """Calculate factor scores for a specific symbol"""
        
        try:
            data = self.market_data[symbol]
            scores = {}
            
            if len(data) < self.config.factor_lookback:
                return scores
            
            # Calculate momentum factor
            if 'momentum' in self.config.factors:
                returns = data['close'].pct_change()
                momentum_score = returns.tail(self.config.factor_lookback).mean()
                scores['momentum'] = momentum_score
            
            # Calculate value factor (simplified P/E proxy)
            if 'value' in self.config.factors:
                # Simplified value score using price volatility as proxy
                price_volatility = data['close'].pct_change().tail(self.config.factor_lookback).std()
                scores['value'] = -price_volatility  # Lower volatility = higher value score
            
            # Calculate quality factor (simplified using price stability)
            if 'quality' in self.config.factors:
                price_stability = 1.0 / (1.0 + data['close'].pct_change().tail(self.config.factor_lookback).std())
                scores['quality'] = price_stability
            
            # Calculate volatility factor
            if 'volatility' in self.config.factors:
                volatility = data['close'].pct_change().tail(self.config.factor_lookback).std()
                scores['volatility'] = -volatility  # Lower volatility = higher score
            
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
                        quantity=self.config.base_position_pct,
                        timestamp=datetime.now(),
                        metadata={
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
