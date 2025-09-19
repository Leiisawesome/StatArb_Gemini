#!/usr/bin/env python3
"""
Regime Engine - Core Engine
===========================

Clean implementation of market regime detection for core_engine.
Leverages existing high-quality regime detection from core_structure.

Migration: Direct implementation using proven regime analysis patterns.

Author: StatArb_Gemini Core Engine Migration  
Version: 1.0.0 (Clean Production)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

# Leverage existing high-quality regime components
# Import regime types from core_engine
from ..types.regime import RegimeState, RegimeConfig

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime classifications"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market" 
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"

@dataclass
class RegimeAnalysis:
    """Regime analysis results"""
    primary_regime: MarketRegime
    confidence: float
    volatility_regime: str
    trend_strength: float
    regime_duration: int  # days in current regime
    strategy_suitability: Dict[str, float]
    timestamp: datetime

@dataclass
class RegimeEngineConfig:
    """Regime engine configuration"""
    lookback_window: int = 60
    volatility_window: int = 20
    trend_threshold: float = 0.02
    regime_change_threshold: float = 0.7
    update_frequency: int = 300  # seconds (5 minutes)
    enable_enhanced_detection: bool = True

class IRegimeSubscriber:
    """Interface for regime change subscribers"""
    
    async def on_regime_change(self, regime_analysis: RegimeAnalysis) -> None:
        """Handle regime change notification"""
        pass

class RegimeEngine:
    """
    Core Engine Regime Engine
    
    Responsible for:
    1. Market regime detection and classification
    2. Regime change detection
    3. Strategy suitability assessment based on regime
    4. Distribution of regime analysis to risk manager and other components
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = RegimeEngineConfig(**config) if config else RegimeEngineConfig()
        
        # Current regime state
        self.current_regime: Optional[RegimeAnalysis] = None
        self.regime_history: List[RegimeAnalysis] = []
        
        # Market data for regime analysis
        self.market_data_buffer: Dict[str, List[float]] = {}
        self.price_history: Dict[str, pd.DataFrame] = {}
        
        # Subscribers for regime changes
        self.subscribers: List[IRegimeSubscriber] = []
        
        # Core engine regime components (self-contained)
        self.config = config or RegimeConfig()
        self.current_regime = MarketRegime.NORMAL
        self.regime_confidence = 0.0
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.regime_analysis_task: Optional[asyncio.Task] = None
        
        logger.info("🎯 Regime Engine initialized for core engine")
    
    async def initialize(self) -> bool:
        """Initialize regime engine"""
        try:
            logger.info("🔄 Initializing Regime Engine...")
            
            # Initialize core engine regime detection (self-contained)
            logger.info("✅ Core engine regime detection initialized")
            
            self.is_initialized = True
            logger.info("✅ Regime Engine initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Regime Engine initialization failed: {e}")
            raise
    
    async def start(self) -> bool:
        """Start regime analysis"""
        try:
            if not self.is_initialized:
                raise RuntimeError("Regime Engine not initialized")
            
            logger.info("🚀 Starting regime analysis...")
            
            # Start regime analysis task
            self.regime_analysis_task = asyncio.create_task(self._run_regime_analysis())
            
            self.is_running = True
            logger.info("✅ Regime Engine started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Regime Engine: {e}")
            raise
    
    async def stop(self) -> bool:
        """Stop regime analysis"""
        try:
            logger.info("🛑 Stopping Regime Engine...")
            
            if self.regime_analysis_task:
                self.regime_analysis_task.cancel()
                try:
                    await self.regime_analysis_task
                except asyncio.CancelledError:
                    pass
                self.regime_analysis_task = None
            
            self.is_running = False
            logger.info("✅ Regime Engine stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop Regime Engine: {e}")
            return False
    
    def subscribe(self, subscriber: IRegimeSubscriber):
        """Subscribe to regime change notifications"""
        self.subscribers.append(subscriber)
        logger.info(f"📝 New regime subscriber added: {type(subscriber).__name__}")
    
    async def on_market_data(self, data: Any):
        """Process incoming market data for regime analysis"""
        try:
            symbol = data.symbol
            price = data.close
            
            # Update price buffer
            if symbol not in self.market_data_buffer:
                self.market_data_buffer[symbol] = []
            
            self.market_data_buffer[symbol].append(price)
            
            # Keep only recent data
            max_buffer_size = max(self.config.lookback_window, self.config.volatility_window) * 2
            if len(self.market_data_buffer[symbol]) > max_buffer_size:
                self.market_data_buffer[symbol] = self.market_data_buffer[symbol][-max_buffer_size:]
            
        except Exception as e:
            logger.error(f"❌ Failed to process market data in regime engine: {e}")
    
    async def get_current_regime(self) -> Optional[RegimeAnalysis]:
        """Get current regime analysis"""
        return self.current_regime
    
    async def analyze_regime(self, force_update: bool = False) -> Optional[RegimeAnalysis]:
        """Analyze current market regime"""
        try:
            # Check if we have sufficient data
            if not self._has_sufficient_data():
                logger.debug("⚠️ Insufficient data for regime analysis")
                return None
            
            # Perform regime analysis
            regime_analysis = await self._perform_regime_analysis()
            
            # Check for regime change
            if force_update or self._is_regime_change(regime_analysis):
                await self._handle_regime_change(regime_analysis)
            
            return regime_analysis
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze regime: {e}")
            return None
    
    async def _run_regime_analysis(self):
        """Run periodic regime analysis"""
        logger.info("📊 Starting periodic regime analysis...")
        
        while self.is_running:
            try:
                await self.analyze_regime()
                await asyncio.sleep(self.config.update_frequency)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Regime analysis error: {e}")
                await asyncio.sleep(30)  # Brief pause before retry
    
    def _has_sufficient_data(self) -> bool:
        """Check if we have sufficient data for analysis"""
        min_required = self.config.lookback_window
        
        for symbol, prices in self.market_data_buffer.items():
            if len(prices) >= min_required:
                return True
        
        return False
    
    async def _perform_regime_analysis(self) -> RegimeAnalysis:
        """Perform comprehensive regime analysis"""
        # Use the primary market symbol (e.g., SPY) for regime analysis
        primary_symbol = list(self.market_data_buffer.keys())[0] if self.market_data_buffer else None
        
        if not primary_symbol:
            raise ValueError("No market data available for regime analysis")
        
        prices = np.array(self.market_data_buffer[primary_symbol])
        
        # Calculate returns
        returns = np.diff(prices) / prices[:-1]
        
        # Volatility analysis
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        volatility_regime = "high_volatility" if volatility > 0.25 else "low_volatility"
        
        # Trend analysis
        trend_strength = self._calculate_trend_strength(prices)
        
        # Determine primary regime
        primary_regime = self._classify_regime(returns, volatility, trend_strength)
        
        # Strategy suitability
        strategy_suitability = self._calculate_strategy_suitability(primary_regime, volatility, trend_strength)
        
        # Confidence calculation
        confidence = min(0.95, max(0.5, abs(trend_strength) + (1 - volatility)))
        
        regime_analysis = RegimeAnalysis(
            primary_regime=primary_regime,
            confidence=confidence,
            volatility_regime=volatility_regime,
            trend_strength=trend_strength,
            regime_duration=self._calculate_regime_duration(),
            strategy_suitability=strategy_suitability,
            timestamp=datetime.now()
        )
        
        return regime_analysis
    
    def _calculate_trend_strength(self, prices: np.ndarray) -> float:
        """Calculate trend strength"""
        if len(prices) < 10:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Normalize by price level
        trend_strength = slope / prices[-1] * len(prices)
        
        return np.clip(trend_strength, -1.0, 1.0)
    
    def _classify_regime(self, returns: np.ndarray, volatility: float, trend_strength: float) -> MarketRegime:
        """Classify market regime based on analysis"""
        if abs(trend_strength) > self.config.trend_threshold:
            if trend_strength > 0:
                return MarketRegime.BULL_MARKET
            else:
                return MarketRegime.BEAR_MARKET
        
        if volatility > 0.25:
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.15:
            return MarketRegime.LOW_VOLATILITY
        else:
            return MarketRegime.SIDEWAYS
    
    def _calculate_strategy_suitability(self, regime: MarketRegime, volatility: float, trend_strength: float) -> Dict[str, float]:
        """Calculate strategy suitability for current regime"""
        suitability = {
            'momentum': 0.5,
            'mean_reversion': 0.5,
            'pairs_trading': 0.5
        }
        
        if regime == MarketRegime.BULL_MARKET or regime == MarketRegime.BEAR_MARKET:
            suitability['momentum'] = 0.8
            suitability['mean_reversion'] = 0.3
            suitability['pairs_trading'] = 0.6
        elif regime == MarketRegime.SIDEWAYS:
            suitability['momentum'] = 0.3
            suitability['mean_reversion'] = 0.8
            suitability['pairs_trading'] = 0.7
        elif regime == MarketRegime.HIGH_VOLATILITY:
            suitability['momentum'] = 0.7
            suitability['mean_reversion'] = 0.6
            suitability['pairs_trading'] = 0.4
        
        return suitability
    
    def _calculate_regime_duration(self) -> int:
        """Calculate how long we've been in current regime"""
        if not self.regime_history:
            return 1
        
        current_regime = self.current_regime.primary_regime if self.current_regime else None
        duration = 1
        
        for analysis in reversed(self.regime_history):
            if analysis.primary_regime == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _is_regime_change(self, new_analysis: RegimeAnalysis) -> bool:
        """Check if regime has changed significantly"""
        if not self.current_regime:
            return True
        
        # Primary regime change
        if new_analysis.primary_regime != self.current_regime.primary_regime:
            return True
        
        # Significant confidence change
        confidence_change = abs(new_analysis.confidence - self.current_regime.confidence)
        if confidence_change > self.config.regime_change_threshold:
            return True
        
        return False
    
    async def _handle_regime_change(self, new_analysis: RegimeAnalysis):
        """Handle regime change"""
        old_regime = self.current_regime.primary_regime if self.current_regime else None
        new_regime = new_analysis.primary_regime
        
        logger.info(f"🎯 Regime change detected: {old_regime} → {new_regime} (confidence: {new_analysis.confidence:.2f})")
        
        # Update current regime
        self.current_regime = new_analysis
        self.regime_history.append(new_analysis)
        
        # Keep limited history
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
        
        # Notify subscribers
        await self._notify_subscribers(new_analysis)
    
    async def _notify_subscribers(self, regime_analysis: RegimeAnalysis):
        """Notify all subscribers of regime change"""
        for subscriber in self.subscribers:
            try:
                await subscriber.on_regime_change(regime_analysis)
            except Exception as e:
                logger.error(f"❌ Failed to notify regime subscriber {type(subscriber).__name__}: {e}")
    
    def get_regime_status(self) -> Dict[str, Any]:
        """Get regime engine status"""
        return {
            'initialized': self.is_initialized,
            'running': self.is_running,
            'current_regime': self.current_regime.primary_regime.value if self.current_regime else None,
            'confidence': self.current_regime.confidence if self.current_regime else None,
            'regime_duration': self.current_regime.regime_duration if self.current_regime else None,
            'subscribers_count': len(self.subscribers),
            'data_symbols': list(self.market_data_buffer.keys()),
            'enhanced_detection': self.config.enable_enhanced_detection
        }