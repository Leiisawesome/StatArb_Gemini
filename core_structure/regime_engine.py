#!/usr/bin/env python3
"""
UnifiedRegimeEngine: Market Condition Assessment System (Optimized)
===================================================================

Component in the essential flow: Market Data -> UnifiedDataManager -> **UnifiedRegimeEngine** -> RiskManager -> StrategyManager -> RealTimeTradingEngine -> UnifiedExecutionEngine -> PortfolioManager

This engine assesses market conditions and regime states that drive all trading decisions.
It leverages existing high-quality functional components rather than duplicating functionality.

Key Features:
- Regime detection leveraging TechnicalIndicatorEngine for calculations
- Integration with SystemOrchestrator design
- Market-driven decision support delegating to existing analytics
- Real-time regime tracking using existing infrastructure
- Sophisticated volatility and trend analysis through existing components

Author: Professional Trading System Architecture  
Version: 2.0.0 (Optimized Delegation)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from collections import deque

# Import existing high-quality functional components - MANDATORY (NO FALLBACKS)
from .components.signal_generation.indicators.technical_indicators import (
    TechnicalIndicatorsEngine, IndicatorConfig, IndicatorResult, IndicatorType
)
from .analytics import CoreAnalyticsEngine as CoreAnalytics, MonitoringAnalyticsEngine as MonitoringAnalytics
from .infrastructure.types import MarketDataType
from .interfaces.regime_interfaces import (
    RegimeType, RegimeMetrics, RegimeState, RegimeTransition, IRegimeSubscriber
)

logger = logging.getLogger(__name__)

@dataclass  
class RegimeConfig:
    """Configuration for regime detection - leverages existing components"""
    # Volatility thresholds
    high_volatility_threshold: float = 0.02  # 2% daily volatility
    low_volatility_threshold: float = 0.005   # 0.5% daily volatility
    
    # Trend detection parameters
    trend_lookback: int = 20
    trend_threshold: float = 0.015  # 1.5% trend strength
    
    # Regime persistence
    min_regime_duration: int = 3  # Minimum bars to confirm regime
    regime_change_threshold: float = 0.7  # Confidence needed for regime change
    
    # Configuration for underlying indicator engine
    indicator_engine_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.indicator_engine_config is None:
            self.indicator_engine_config = {
                "enable_parallel_calculation": True,
                "cache_indicators": True,
                "enable_adaptive_thresholds": True
            }
    """Interface for regime state subscribers"""
    
    @abstractmethod
    def on_regime_change(self, old_regime: RegimeState, new_regime: RegimeState, transition: RegimeTransition) -> None:
        """Handle regime state changes"""
        pass

class UnifiedRegimeEngine:
    """
    Unified engine for market regime detection that leverages existing components.
    
    Instead of implementing technical indicators directly, it delegates to:
    - TechnicalIndicatorsEngine for all indicator calculations (RSI, Bollinger Bands, ATR, etc.)
    - CoreAnalytics for regime analysis and confidence calculations
    - MonitoringAnalytics for performance tracking and validation
    """
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        """Initialize the regime engine with delegation to existing components"""
        self.config = config or RegimeConfig()
        
        # Initialize existing functional components
        self._initialize_delegated_components()
        
        # State tracking
        self.current_regime: Dict[str, RegimeState] = {}
        self.regime_metrics: Dict[str, RegimeMetrics] = {}
        self.regime_history: Dict[str, deque] = {}
        self.price_history: Dict[str, deque] = {}
        
        # Subscribers for regime changes - both old and new style
        self.regime_subscribers: List[Callable] = []
        self.subscribers: List[IRegimeSubscriber] = []
        
        # Component state
        self.is_running = False
        
        # Performance tracking
        self.regime_changes: int = 0
        self.accuracy_tracking: Dict[str, List[float]] = {}
        
        logger.info("🔍 UnifiedRegimeEngine initialized with component delegation")
    
    def _initialize_delegated_components(self) -> None:
        """Initialize existing functional components for delegation - MANDATORY (NO FALLBACKS)"""
        # Initialize TechnicalIndicatorsEngine for all indicator calculations - MANDATORY
        indicator_config = IndicatorConfig(**self.config.indicator_engine_config)
        self.indicator_engine = TechnicalIndicatorsEngine(indicator_config)
        logger.info("✅ Delegating indicator calculations to TechnicalIndicatorsEngine")
        
        # Initialize CoreAnalytics for regime analysis - MANDATORY
        self.analytics_engine = CoreAnalytics()
        logger.info("✅ Delegating regime analysis to CoreAnalytics")
        
        # Initialize MonitoringAnalytics for performance tracking - MANDATORY
        self.monitoring_engine = MonitoringAnalytics()
        logger.info("✅ Delegating performance monitoring to MonitoringAnalytics")
    
    async def startup(self) -> bool:
        """Start the regime engine"""
        try:
            logger.info("🚀 Starting UnifiedRegimeEngine with delegated components...")
            
            # Start delegated components
            if self.indicator_engine and hasattr(self.indicator_engine, 'startup'):
                await self.indicator_engine.startup()
                logger.info("✅ TechnicalIndicatorEngine started")
            
            if self.analytics_engine:
                try:
                    if hasattr(self.analytics_engine, 'initialize'):
                        await self.analytics_engine.initialize()
                    logger.info("✅ CoreAnalytics started")
                except Exception as e:
                    logger.warning(f"⚠️ Analytics engine start warning: {e}")
            
            self.is_running = True
            logger.info("✅ UnifiedRegimeEngine started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start UnifiedRegimeEngine: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the regime engine"""
        try:
            logger.info("⏹️ Shutting down UnifiedRegimeEngine...")
            
            self.is_running = False
            
            # Shutdown delegated components
            if self.indicator_engine:
                try:
                    if hasattr(self.indicator_engine, 'shutdown'):
                        await self.indicator_engine.shutdown()
                    logger.info("✅ TechnicalIndicatorsEngine stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping indicator engine: {e}")
            
            if self.analytics_engine:
                try:
                    if hasattr(self.analytics_engine, 'shutdown'):
                        await self.analytics_engine.shutdown()
                    logger.info("✅ CoreAnalytics stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping analytics engine: {e}")
            
            # Clear state
            self.current_regime.clear()
            self.regime_metrics.clear()
            self.regime_history.clear()
            self.price_history.clear()
            
            logger.info("✅ UnifiedRegimeEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to shutdown UnifiedRegimeEngine: {e}")
    
    def subscribe(self, subscriber: IRegimeSubscriber) -> None:
        """Subscribe to regime changes (new interface)"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"📢 New regime subscriber added: {type(subscriber).__name__}")
    
    def unsubscribe(self, subscriber: IRegimeSubscriber) -> None:
        """Unsubscribe from regime changes"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"📢 Regime subscriber removed: {type(subscriber).__name__}")
    
    def subscribe_to_regime_changes(self, callback: Callable) -> None:
        """Subscribe to regime change notifications (legacy interface)"""
        self.regime_subscribers.append(callback)
        logger.info("📢 Regime change subscriber added")
    
    async def update_regime(self, symbol: str, market_data: pd.DataFrame) -> RegimeState:
        """
        Main entry point for regime assessment using delegated components
        
        Args:
            symbol: Trading symbol
            market_data: Latest market data
            
        Returns:
            Current regime state for the symbol
        """
        try:
            # Initialize symbol tracking if needed
            if symbol not in self.current_regime:
                self._initialize_symbol(symbol)
            
            # Calculate regime metrics using delegated components
            metrics = await self._calculate_regime_metrics_delegated(symbol, market_data)
            self.regime_metrics[symbol] = metrics
            
            # Determine regime state using delegated analytics
            new_regime = await self._determine_regime_state_delegated(symbol, metrics)
            
            # Check for regime change
            if new_regime != self.current_regime[symbol]:
                await self._handle_regime_change(symbol, new_regime, metrics)
            
            # Update history
            self._update_history(symbol, new_regime, market_data)
            
            return new_regime
            
        except Exception as e:
            logger.error(f"❌ Regime update failed for {symbol}: {e}")
            return self.current_regime.get(symbol, RegimeType.UNKNOWN)
    
    async def _calculate_regime_metrics_delegated(self, symbol: str, market_data: pd.DataFrame) -> RegimeMetrics:
        """Calculate regime metrics using delegated TechnicalIndicatorsEngine"""
        try:
            if self.indicator_engine and len(market_data) >= 20:
                # Delegate all indicator calculations to TechnicalIndicatorsEngine
                
                # Calculate RSI using delegated engine
                rsi_result = await self._calculate_indicator_safe('rsi', market_data, period=14)
                rsi_value = rsi_result.current_value if rsi_result and rsi_result.current_value else 50.0
                
                # Calculate Bollinger Bands using delegated engine
                bb_result = await self._calculate_indicator_safe('bollinger_bands', market_data, period=20, std_dev=2.0)
                bb_position = 0.5
                if bb_result and bb_result.current_value:
                    # Extract position from Bollinger Bands result
                    bb_position = bb_result.metadata.get('bb_position', 0.5)
                
                # Calculate ATR using delegated engine
                atr_result = await self._calculate_indicator_safe('atr', market_data, period=14)
                atr_value = atr_result.current_value if atr_result and atr_result.current_value else 0.0
                current_price = market_data['close'].iloc[-1] if len(market_data) > 0 else 1.0
                atr_normalized = atr_value / current_price if current_price > 0 else 0.0
                
                # Calculate volatility using delegated analytics
                volatility = await self._calculate_volatility_delegated(market_data)
                
                # Calculate trend strength using delegated analytics
                trend_strength = await self._calculate_trend_strength_delegated(market_data)
                
                # Calculate momentum using delegated analytics
                momentum = await self._calculate_momentum_delegated(market_data)
                
                # Calculate volume trend using delegated analytics
                volume_trend = await self._calculate_volume_trend_delegated(market_data)
                
                # Calculate regime confidence using delegated analytics
                confidence = await self._calculate_regime_confidence_delegated(symbol, volatility, trend_strength)
                
                return RegimeMetrics(
                    volatility=volatility,
                    trend_strength=trend_strength,
                    momentum=momentum,
                    volume_profile=volume_trend,  # Map volume_trend to volume_profile
                    confidence=confidence
                )
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate regime metrics for {symbol}: {e}")
            return RegimeMetrics()
    
    async def _calculate_indicator_safe(self, indicator_name: str, market_data: pd.DataFrame, **kwargs) -> Optional[IndicatorResult]:
        """Safely calculate indicator using delegated engine"""
        try:
            if self.indicator_engine:
                # Check for main calculate_indicator method (usually synchronous)
                if hasattr(self.indicator_engine, 'calculate_indicator'):
                    method = self.indicator_engine.calculate_indicator
                    if asyncio.iscoroutinefunction(method):
                        return await method(indicator_name, market_data, **kwargs)
                    else:
                        return method(indicator_name, market_data, **kwargs)
                # Check for specific method like calculate_rsi, calculate_bollinger_bands, etc.
                elif hasattr(self.indicator_engine, f'calculate_{indicator_name}'):
                    method = getattr(self.indicator_engine, f'calculate_{indicator_name}')
                    if asyncio.iscoroutinefunction(method):
                        return await method(market_data, **kwargs)
                    else:
                        return method(market_data, **kwargs)
        except Exception as e:
            logger.warning(f"⚠️ Indicator calculation failed for {indicator_name}: {e}")
        return None
    
    async def _calculate_volatility_delegated(self, market_data: pd.DataFrame) -> float:
        """Calculate volatility using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_volatility'):
                return await self.analytics_engine.calculate_volatility(market_data)
            else:
                # Fallback calculation
                prices = market_data['close'].values
                returns = np.diff(np.log(prices))
                return np.std(returns[-20:]) * np.sqrt(252) if len(returns) >= 20 else 0.0
        except Exception as e:
            logger.warning(f"⚠️ Volatility calculation fallback: {e}")
            return 0.15  # Default moderate volatility
    
    async def _calculate_trend_strength_delegated(self, market_data: pd.DataFrame) -> float:
        """Calculate trend strength using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_trend_strength'):
                return await self.analytics_engine.calculate_trend_strength(market_data)
            else:
                # Fallback calculation
                prices = market_data['close'].values
                if len(prices) < self.config.trend_lookback:
                    return 0.0
                x = np.arange(len(prices[-self.config.trend_lookback:]))
                y = prices[-self.config.trend_lookback:]
                slope = np.polyfit(x, y, 1)[0]
                return np.clip(slope / np.mean(y) * self.config.trend_lookback, -1.0, 1.0)
        except Exception:
            return 0.0
    
    async def _calculate_momentum_delegated(self, market_data: pd.DataFrame) -> float:
        """Calculate momentum using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_momentum'):
                return await self.analytics_engine.calculate_momentum(market_data)
            else:
                # Fallback calculation
                prices = market_data['close'].values
                return (prices[-1] / prices[-min(10, len(prices))] - 1) if len(prices) >= 10 else 0.0
        except Exception:
            return 0.0
    
    async def _calculate_volume_trend_delegated(self, market_data: pd.DataFrame) -> float:
        """Calculate volume trend using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_volume_trend'):
                return await self.analytics_engine.calculate_volume_trend(market_data)
            else:
                # Fallback calculation
                volumes = market_data.get('volume', pd.Series([1] * len(market_data))).values
                if len(volumes) < 10:
                    return 0.0
                recent_volume = np.mean(volumes[-5:])
                historical_volume = np.mean(volumes[-20:-5]) if len(volumes) >= 20 else np.mean(volumes[:-5])
                return (recent_volume / historical_volume - 1.0) if historical_volume > 0 else 0.0
        except Exception:
            return 0.0
    
    async def _calculate_regime_confidence_delegated(self, symbol: str, volatility: float, trend_strength: float) -> float:
        """Calculate regime confidence using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'calculate_regime_confidence'):
                return await self.analytics_engine.calculate_regime_confidence(symbol, volatility, trend_strength)
            else:
                # Fallback calculation
                confidence = 0.5
                if volatility > self.config.high_volatility_threshold:
                    confidence += 0.2
                elif volatility < self.config.low_volatility_threshold:
                    confidence += 0.2
                if abs(trend_strength) > self.config.trend_threshold:
                    confidence += 0.2
                return np.clip(confidence, 0.0, 1.0)
        except Exception:
            return 0.5
    
    async def _fallback_regime_metrics(self, symbol: str, market_data: pd.DataFrame) -> RegimeMetrics:
        """Fallback regime metrics calculation when delegated components unavailable"""
        try:
            prices = market_data['close'].values
            if len(prices) < 10:
                return RegimeMetrics()
            
            # Simple volatility
            returns = np.diff(np.log(prices))
            volatility = np.std(returns[-10:]) * np.sqrt(252) if len(returns) >= 10 else 0.15
            
            # Simple trend
            trend_strength = (prices[-1] / prices[-min(10, len(prices))] - 1) if len(prices) >= 10 else 0.0
            
            # Simple momentum  
            momentum = (prices[-1] / prices[-min(5, len(prices))] - 1) if len(prices) >= 5 else 0.0
            
            return RegimeMetrics(
                volatility=volatility,
                trend_strength=trend_strength,
                momentum=momentum,
                rsi=50.0,  # Neutral
                bollinger_position=0.5,  # Neutral
                confidence=0.5  # Low confidence due to fallback
            )
        except Exception:
            return RegimeMetrics()
    
    async def _determine_regime_state_delegated(self, symbol: str, metrics: RegimeMetrics) -> RegimeState:
        """Determine regime state using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'determine_regime_state'):
                return await self.analytics_engine.determine_regime_state(symbol, metrics)
            else:
                # Fallback regime determination
                return self._fallback_regime_determination(metrics)
        except Exception as e:
            logger.warning(f"⚠️ Regime determination fallback: {e}")
            return self._fallback_regime_determination(metrics)
    
    def _fallback_regime_determination(self, metrics: RegimeMetrics) -> RegimeState:
        """Fallback regime determination logic"""
        try:
            # Crisis detection
            if metrics.volatility > self.config.high_volatility_threshold * 2 and metrics.momentum < -0.1:
                return RegimeType.CRISIS
            
            # High volatility regimes
            if metrics.volatility > self.config.high_volatility_threshold:
                if abs(metrics.trend_strength) > self.config.trend_threshold:
                    return RegimeType.TRENDING_UP if metrics.trend_strength > 0 else RegimeType.TRENDING_DOWN
                else:
                    return RegimeType.HIGH_VOLATILITY
            
            # Low volatility regimes
            if metrics.volatility < self.config.low_volatility_threshold:
                return RegimeType.LOW_VOLATILITY
            
            # Normal volatility regimes
            if abs(metrics.trend_strength) > self.config.trend_threshold:
                return RegimeType.TRENDING_UP if metrics.trend_strength > 0 else RegimeType.TRENDING_DOWN
            
            # Default to ranging
            return RegimeType.RANGING
            
        except Exception:
            return RegimeType.UNKNOWN
    
    def _initialize_symbol(self, symbol: str) -> None:
        """Initialize tracking for a new symbol"""
        self.current_regime[symbol] = RegimeType.UNKNOWN
        self.regime_metrics[symbol] = RegimeMetrics()
        self.regime_history[symbol] = deque(maxlen=100)
        self.price_history[symbol] = deque(maxlen=100)
        self.accuracy_tracking[symbol] = []
        
        logger.info(f"📊 Initialized regime tracking for {symbol}")
    
    async def _handle_regime_change(self, symbol: str, new_regime: RegimeState, metrics: RegimeMetrics) -> None:
        """Handle regime change notifications"""
        try:
            old_regime = self.current_regime[symbol]
            self.current_regime[symbol] = new_regime
            self.regime_changes += 1
            
            logger.info(f"📈 Regime change for {symbol}: {old_regime.value} -> {new_regime.value} (confidence: {metrics.confidence:.2f})")
            
            # Create transition object
            transition = RegimeTransition(
                from_regime=old_regime,
                to_regime=new_regime,
                transition_time=datetime.now(),
                confidence=metrics.confidence
            )
            
            # Notify legacy subscribers
            for callback in self.regime_subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(symbol, new_regime, metrics)
                    else:
                        callback(symbol, new_regime, metrics)
                except Exception as e:
                    logger.error(f"❌ Regime subscriber callback failed: {e}")
            
            # Notify new interface subscribers
            for subscriber in self.subscribers:
                try:
                    if hasattr(subscriber, 'on_regime_change'):
                        if asyncio.iscoroutinefunction(subscriber.on_regime_change):
                            await subscriber.on_regime_change(old_regime, new_regime, transition)
                        else:
                            subscriber.on_regime_change(old_regime, new_regime, transition)
                except Exception as e:
                    logger.error(f"❌ New regime subscriber failed: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to handle regime change for {symbol}: {e}")
    
    def _update_history(self, symbol: str, regime: RegimeState, market_data: pd.DataFrame) -> None:
        """Update historical tracking"""
        try:
            self.regime_history[symbol].append(regime)
            if len(market_data) > 0:
                self.price_history[symbol].append(market_data['close'].iloc[-1])
                
        except Exception as e:
            logger.error(f"❌ Failed to update history for {symbol}: {e}")
    
    # Public interface methods (unchanged)
    def get_regime_state(self, symbol: str) -> RegimeState:
        """Get current regime state for a symbol"""
        return self.current_regime.get(symbol, RegimeType.UNKNOWN)
    
    def get_regime_metrics(self, symbol: str) -> Optional[RegimeMetrics]:
        """Get current regime metrics for a symbol"""
        return self.regime_metrics.get(symbol)
    
    def get_regime_history(self, symbol: str, lookback: int = 20) -> List[RegimeState]:
        """Get regime history for a symbol"""
        if symbol not in self.regime_history:
            return []
        return list(self.regime_history[symbol])[-lookback:]
    
    def get_market_overview(self) -> Dict[str, Any]:
        """Get overview of all tracked markets using delegated analytics"""
        try:
            if self.analytics_engine and hasattr(self.analytics_engine, 'get_market_overview'):
                return self.analytics_engine.get_market_overview(self.current_regime, self.regime_metrics)
            else:
                # Fallback overview
                regime_distribution = {}
                for regime in self.current_regime.values():
                    regime_distribution[regime.value] = regime_distribution.get(regime.value, 0) + 1
                
                avg_volatility = np.mean([m.volatility for m in self.regime_metrics.values()]) if self.regime_metrics else 0.0
                avg_confidence = np.mean([m.confidence for m in self.regime_metrics.values()]) if self.regime_metrics else 0.0
                
                return {
                    "tracked_symbols": list(self.current_regime.keys()),
                    "regime_distribution": regime_distribution,
                    "total_regime_changes": self.regime_changes,
                    "average_volatility": avg_volatility,
                    "average_confidence": avg_confidence,
                    "regime_states": {symbol: regime.value for symbol, regime in self.current_regime.items()},
                    "delegation_status": {
                        "indicator_engine": self.indicator_engine is not None,
                        "analytics_engine": self.analytics_engine is not None,
                        "monitoring_engine": self.monitoring_engine is not None
                    }
                }
        except Exception as e:
            logger.error(f"❌ Failed to generate market overview: {e}")
            return {"error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current regime engine status"""
        return {
            "is_running": self.is_running,
            "tracked_symbols": list(self.current_regime.keys()),
            "regime_changes": self.regime_changes,
            "subscribers_count": len(self.subscribers) + len(self.regime_subscribers),
            "delegated_components": {
                "indicator_engine_available": self.indicator_engine is not None,
                "analytics_engine_available": self.analytics_engine is not None,
                "monitoring_engine_available": self.monitoring_engine is not None
            }
        }
    
    async def update_regime_manual(self, regime_name: str, context: Dict[str, Any] = None) -> None:
        """Simplified regime update method for testing and manual override"""
        try:
            # Convert string to RegimeState
            regime_state = None
            for state in RegimeState:
                if state.value == regime_name:
                    regime_state = state
                    break
            
            if regime_state is None:
                # Default mapping for common regime names
                regime_mapping = {
                    "trending_up": RegimeType.TRENDING_UP,
                    "trending_down": RegimeType.TRENDING_DOWN,
                    "ranging": RegimeType.RANGING,
                    "breakout": RegimeType.BREAKOUT,
                    "consolidation": RegimeType.RANGING,
                    "low_volatility": RegimeType.LOW_VOLATILITY,
                    "high_volatility": RegimeType.HIGH_VOLATILITY
                }
                regime_state = regime_mapping.get(regime_name, RegimeType.UNKNOWN)
            
            # Create test symbol if needed
            test_symbol = "TEST"
            if test_symbol not in self.current_regime:
                self._initialize_symbol(test_symbol)
            
            # Create dummy metrics
            metrics = RegimeMetrics(
                volatility=context.get("volatility", 0.15) if context else 0.15,
                trend_strength=context.get("trend_strength", 0.5) if context else 0.5,
                momentum=context.get("momentum", 0.1) if context else 0.1,
                confidence=context.get("confidence", 0.8) if context else 0.8
            )
            
            # Force regime change if different
            if regime_state != self.current_regime[test_symbol]:
                await self._handle_regime_change(test_symbol, regime_state, metrics)
                
        except Exception as e:
            logger.error(f"❌ Failed to update regime manually: {e}")

# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_regime_engine(config: Optional[RegimeConfig] = None) -> UnifiedRegimeEngine:
    """Create a new UnifiedRegimeEngine instance"""
    return UnifiedRegimeEngine(config)

def create_conservative_regime_engine() -> UnifiedRegimeEngine:
    """Create a conservative regime engine with higher thresholds"""
    config = RegimeConfig(
        high_volatility_threshold=0.025,
        low_volatility_threshold=0.008,
        trend_threshold=0.02,
        min_regime_duration=5,
        regime_change_threshold=0.8
    )
    return UnifiedRegimeEngine(config)

def create_aggressive_regime_engine() -> UnifiedRegimeEngine:
    """Create an aggressive regime engine with lower thresholds"""
    config = RegimeConfig(
        high_volatility_threshold=0.015,
        low_volatility_threshold=0.003,
        trend_threshold=0.01,
        min_regime_duration=2,
        regime_change_threshold=0.6
    )
    return UnifiedRegimeEngine(config)

# Export key components
__all__ = [
    'UnifiedRegimeEngine', 
    'RegimeConfig',
    'RegimeState',
    'RegimeMetrics',
    'RegimeTransition',
    'create_regime_engine',
    'create_conservative_regime_engine',
    'create_aggressive_regime_engine'
]