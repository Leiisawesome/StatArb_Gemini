"""
Enhanced Volatility Strategy with ISystemComponent Integration
============================================================

Professional volatility-based strategy that implements ISystemComponent interface
for seamless orchestrator integration and institutional-grade lifecycle management.

Key Features:
- Volatility surface analysis
- Volatility regime detection
- Risk-adjusted volatility trading
- Dynamic hedging strategies
- Professional volatility modeling

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

logger = logging.getLogger(__name__)


@dataclass
class VolatilityConfig(StrategyConfig):
    """Enhanced Volatility Configuration"""
    
    # Volatility parameters
    volatility_lookback: int = 20           # Volatility calculation period
    volatility_threshold: float = 0.02      # Volatility threshold (2%)
    regime_detection: bool = True           # Enable volatility regime detection
    
    # Position sizing
    base_position_pct: float = 0.025        # Base position size (2.5%)
    max_position_pct: float = 0.07          # Maximum position size (7%)
    volatility_scaling: bool = True         # Scale positions by volatility
    
    # Risk management
    vol_target: float = 0.15                # Target portfolio volatility (15%)
    
    # Asset universe
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])


class EnhancedVolatilityStrategy(EnhancedBaseStrategy):
    """Enhanced Volatility Strategy with ISystemComponent Integration"""
    
    def __init__(self, config: VolatilityConfig):
        """Initialize enhanced volatility strategy"""
        
        # Initialize base strategy
        super().__init__(config)
        self.config: VolatilityConfig = config
        
        # Strategy-specific state
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.volatility_data: Dict[str, Dict[str, float]] = {}
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🧠 Enhanced Volatility Strategy {self.strategy_id} initialized")
    
    # ========================================
    # STRATEGY-SPECIFIC LIFECYCLE HOOKS
    # ========================================
    
    async def _initialize_strategy_components(self) -> bool:
        """Initialize strategy-specific components"""
        
        try:
            logger.info(f"🔄 Initializing Volatility components for {self.strategy_id}...")
            
            if not self.config.symbols:
                logger.error("❌ No symbols configured for volatility strategy")
                return False
            
            self._initialize_data_structures()
            
            logger.info(f"✅ Volatility components initialized for {len(self.config.symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"❌ Volatility component initialization failed: {e}")
            return False
    
    async def _start_strategy_operations(self) -> bool:
        """Start strategy-specific operations"""
        
        try:
            logger.info(f"🚀 Starting Volatility operations for {self.strategy_id}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Volatility operations start failed: {e}")
            return False
    
    async def _stop_strategy_operations(self) -> None:
        """Stop strategy-specific operations"""
        
        try:
            logger.info(f"🔄 Stopping Volatility operations for {self.strategy_id}...")
            await self._close_all_positions()
            logger.info(f"✅ Volatility operations stopped")
            
        except Exception as e:
            logger.error(f"❌ Volatility operations stop failed: {e}")
    
    async def _check_strategy_health(self) -> Dict[str, Any]:
        """Check strategy-specific health"""
        
        try:
            return {
                'strategy_healthy': True,
                'symbols_tracked': len(self.config.symbols),
                'active_positions': len(self.active_positions),
                'volatility_data_available': len(self.volatility_data),
                'avg_volatility': self._calculate_avg_volatility()
            }
            
        except Exception as e:
            return {'strategy_healthy': False, 'error': str(e)}
    
    def _get_strategy_config_summary(self) -> Dict[str, Any]:
        """Get strategy-specific configuration summary"""
        
        return {
            'strategy_type': 'Enhanced Volatility',
            'symbols_count': len(self.config.symbols),
            'volatility_lookback': self.config.volatility_lookback,
            'volatility_threshold': self.config.volatility_threshold,
            'regime_detection': self.config.regime_detection,
            'vol_target': self.config.vol_target
        }
    
    def _validate_strategy_config(self) -> bool:
        """Validate strategy-specific configuration"""
        
        try:
            if self.config.volatility_threshold <= 0:
                logger.error("Volatility threshold must be positive")
                return False
            
            if self.config.volatility_lookback < 10:
                logger.error("Volatility lookback must be at least 10")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    # ========================================
    # ABSTRACT METHOD IMPLEMENTATIONS
    # ========================================
    
    async def generate_signals(self, market_data: Dict[str, pd.DataFrame]) -> List[StrategySignal]:
        """Generate volatility-based signals"""
        
        start_time = datetime.now()
        signals = []
        
        try:
            # Update market data
            self._update_market_data(market_data)
            
            # Calculate volatility metrics
            self._calculate_volatility_metrics()
            
            # Generate signals based on volatility analysis
            signals = await self._generate_volatility_signals()
            
            # Update performance metrics
            generation_time = (datetime.now() - start_time).total_seconds()
            self.track_signal_generation_time(generation_time)
            
            logger.info(f"📊 Generated {len(signals)} Volatility signals in {generation_time:.3f}s")
            
            return signals
            
        except Exception as e:
            self._log_error("Signal generation failed", e)
            return []
    
    async def update_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """Update existing positions based on market data"""
        
        try:
            self._update_market_data(market_data)
            self._calculate_volatility_metrics()
            
        except Exception as e:
            self._log_error("Position update failed", e)
    
    def calculate_position_size(self, signal: StrategySignal, market_data: Dict[str, pd.DataFrame]) -> float:
        """Calculate position size for a given signal"""
        
        try:
            symbol = signal.symbol
            base_size = self.config.base_position_pct
            
            # Volatility-adjusted sizing
            if self.config.volatility_scaling and symbol in self.volatility_data:
                vol_data = self.volatility_data[symbol]
                current_vol = vol_data.get('realized_volatility', 0.02)
                
                # Inverse volatility scaling
                vol_adjustment = self.config.vol_target / max(current_vol, 0.01)
                base_size *= min(vol_adjustment, 2.0)  # Cap adjustment
            
            return min(base_size, self.config.max_position_pct)
            
        except Exception as e:
            self._log_error("Position size calculation failed", e)
            return 0.0
    
    # ========================================
    # VOLATILITY CALCULATION METHODS
    # ========================================
    
    def _calculate_volatility_metrics(self) -> None:
        """Calculate volatility metrics for all symbols"""
        
        for symbol in self.config.symbols:
            if symbol in self.market_data:
                self.volatility_data[symbol] = self._calculate_symbol_volatility(symbol)
    
    def _calculate_symbol_volatility(self, symbol: str) -> Dict[str, float]:
        """Calculate volatility metrics for a specific symbol"""
        
        try:
            data = self.market_data[symbol]
            vol_data = {}
            
            if len(data) < self.config.volatility_lookback:
                return vol_data
            
            # Calculate returns
            returns = data['close'].pct_change().dropna()
            
            # Realized volatility
            realized_vol = returns.tail(self.config.volatility_lookback).std() * np.sqrt(252)
            vol_data['realized_volatility'] = realized_vol
            
            # Historical volatility (longer period)
            if len(returns) >= 60:
                historical_vol = returns.tail(60).std() * np.sqrt(252)
                vol_data['historical_volatility'] = historical_vol
                
                # Volatility ratio
                vol_data['volatility_ratio'] = realized_vol / historical_vol if historical_vol > 0 else 1.0
            
            # Volatility regime
            if self.config.regime_detection:
                vol_regime = self._detect_volatility_regime(returns)
                vol_data['volatility_regime'] = vol_regime
            
            return vol_data
            
        except Exception as e:
            logger.error(f"Volatility calculation failed for {symbol}: {e}")
            return {}
    
    def _detect_volatility_regime(self, returns: pd.Series) -> str:
        """Detect volatility regime (low, normal, high)"""
        
        try:
            if len(returns) < 60:
                return 'normal'
            
            # Calculate rolling volatility
            rolling_vol = returns.rolling(20).std() * np.sqrt(252)
            current_vol = rolling_vol.iloc[-1]
            
            # Calculate percentiles
            vol_25th = rolling_vol.quantile(0.25)
            vol_75th = rolling_vol.quantile(0.75)
            
            if current_vol < vol_25th:
                return 'low'
            elif current_vol > vol_75th:
                return 'high'
            else:
                return 'normal'
                
        except Exception as e:
            logger.error(f"Volatility regime detection failed: {e}")
            return 'normal'
    
    async def _generate_volatility_signals(self) -> List[StrategySignal]:
        """Generate signals based on volatility analysis"""
        
        signals = []
        
        try:
            for symbol in self.config.symbols:
                if symbol in self.volatility_data:
                    vol_data = self.volatility_data[symbol]
                    
                    # Skip if already have position
                    if symbol in self.active_positions:
                        continue
                    
                    # Generate signals based on volatility conditions
                    signal = self._analyze_volatility_opportunity(symbol, vol_data)
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self._log_error("Volatility signal generation failed", e)
            return []
    
    def _analyze_volatility_opportunity(self, symbol: str, vol_data: Dict[str, float]) -> Optional[StrategySignal]:
        """Analyze volatility opportunity for a symbol"""
        
        try:
            realized_vol = vol_data.get('realized_volatility', 0)
            vol_ratio = vol_data.get('volatility_ratio', 1.0)
            vol_regime = vol_data.get('volatility_regime', 'normal')
            
            # Low volatility opportunity (expect volatility expansion)
            if (vol_regime == 'low' and 
                vol_ratio < 0.8 and 
                realized_vol < self.config.volatility_threshold):
                
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=0.7,
                    confidence=0.75,
                    target_quantity=self.config.base_position_pct,
                    timestamp=datetime.now(),
                    additional_data={
                        'signal_reason': 'low_volatility_expansion',
                        'realized_volatility': realized_vol,
                        'volatility_ratio': vol_ratio,
                        'volatility_regime': vol_regime
                    }
                )
            
            # High volatility opportunity (expect volatility contraction)
            elif (vol_regime == 'high' and 
                  vol_ratio > 1.5 and 
                  realized_vol > self.config.volatility_threshold * 2):
                
                return StrategySignal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    strength=0.6,
                    confidence=0.7,
                    target_quantity=self.config.base_position_pct,
                    timestamp=datetime.now(),
                    additional_data={
                        'signal_reason': 'high_volatility_contraction',
                        'realized_volatility': realized_vol,
                        'volatility_ratio': vol_ratio,
                        'volatility_regime': vol_regime
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Volatility opportunity analysis failed for {symbol}: {e}")
            return None
    
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
        self.volatility_data.clear()
        self.active_positions.clear()
    
    def _calculate_avg_volatility(self) -> float:
        """Calculate average volatility across symbols"""
        
        if not self.volatility_data:
            return 0.0
        
        volatilities = []
        for vol_data in self.volatility_data.values():
            if 'realized_volatility' in vol_data:
                volatilities.append(vol_data['realized_volatility'])
        
        return np.mean(volatilities) if volatilities else 0.0
    
    async def _close_all_positions(self) -> None:
        """Close all active positions"""
        
        logger.info(f"🔄 Closing {len(self.active_positions)} active positions")
        self.active_positions.clear()
    
    # ========================================
    # STRATEGY-SPECIFIC METHODS
    # ========================================
    
    def get_volatility_summary(self) -> Dict[str, Any]:
        """Get comprehensive volatility strategy summary"""
        
        return {
            'strategy_id': self.strategy_id,
            'strategy_type': 'Enhanced Volatility',
            'symbols_tracked': len(self.config.symbols),
            'active_positions': len(self.active_positions),
            'avg_volatility': self._calculate_avg_volatility(),
            'performance_summary': self.get_performance_summary(),
            'volatility_data': self.volatility_data
        }
