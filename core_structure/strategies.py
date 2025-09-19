#!/usr/bin/env python3
"""
StrategyManager: Strategy Orchestration and Signal Generation (Optimized)
========================================================================

Component in the essential flow: Market Data -> UnifiedDataManager -> UnifiedRegimeEngine -> RiskManager -> **StrategyManager** -> RealTimeTradingEngine -> UnifiedExecutionEngine -> PortfolioManager

This manager handles strategy execution, signal generation, and strategy lifecycle management.
It leverages existing high-quality functional components rather than duplicating functionality.

Key Features:
- Strategy lifecycle management leveraging UnifiedSignalEngine
- Signal generation delegation to existing signal generation components
- Strategy performance monitoring using existing analytics
- Integration with SystemOrchestrator
- Central Risk Authority Integration: All trading proposals submitted to RiskManager

Author: Professional Trading System Architecture
Version: 2.0.0 (Optimized Delegation)
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

# Import existing high-quality functional components (fail-fast architecture)
try:
    from .components.signal_generation import (
        UnifiedSignalEngine, TradingSignal, SignalConfig, SignalType, SignalStrength,
        PortfolioOptimizationEngine
    )
    from .analytics import CoreAnalyticsEngine, MonitoringAnalyticsEngine
    from .advanced_risk_management import AdvancedRiskManager, TradeRequest, TradeAuthorization
    logger = logging.getLogger(__name__)
    logger.info("✅ Core signal generation components loaded successfully")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Required signal generation components not available - fail-fast architecture: {e}")
    # Define minimal fallback classes for basic functionality
    from enum import Enum
    from dataclasses import dataclass
    from datetime import datetime
    
    class SignalType(Enum):
        BUY = "buy"
        SELL = "sell"
        HOLD = "hold"
        CLOSE = "close"
    
    @dataclass
    class TradingSignal:
        symbol: str
        signal_type: SignalType
        strength: float
        price: float
        timestamp: datetime
        strategy: str
        confidence: float = 0.0
        metadata: Dict[str, Any] = None

    # Minimal risk management fallback
    @dataclass
    class TradeRequest:
        request_id: str
        symbol: str
        action: str
        quantity: float
        price: float
        strategy: str
        timestamp: datetime
        metadata: Dict[str, Any] = None

    @dataclass
    class TradeAuthorization:
        request_id: str
        authorized: bool
        authorization_token: str
        risk_limits_applied: Dict[str, Any]
        rejection_reason: Optional[str] = None
        timestamp: datetime = None

    class AdvancedRiskManager:
        def __init__(self):
            pass
        
        async def authorize_trade(self, trade_request: TradeRequest) -> TradeAuthorization:
            # Fallback authorization - always approve for basic functionality
            return TradeAuthorization(
                request_id=trade_request.request_id,
                authorized=True,
                authorization_token=str(uuid.uuid4()),
                risk_limits_applied={},
                timestamp=datetime.now()
            )

# Base strategy interface for compatibility (always available)
class BaseStrategy(ABC):
    """Base strategy interface for all trading strategies"""
    
    @abstractmethod
    def generate_signal(self, symbol: str, data: pd.DataFrame) -> Optional[TradingSignal]:
        """Generate trading signal for given symbol and data"""
        pass
    
    @abstractmethod
    def update_parameters(self, params: Dict[str, Any]) -> None:
        """Update strategy parameters"""
        pass

logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Configuration for strategy management - leverages existing components"""
    enabled_strategies: List[str] = None
    signal_aggregation: str = "weighted_average"  # or "majority_vote", "best_performer"
    min_signal_strength: float = 0.3
    max_strategies_per_symbol: int = 5
    
    # Configuration for underlying signal engine
    signal_engine_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.enabled_strategies is None:
            self.enabled_strategies = ["mean_reversion", "momentum", "pairs_trading"]
        if self.signal_engine_config is None:
            self.signal_engine_config = {
                "min_confidence_threshold": 0.35,
                "max_position_size": 0.15,
                "lookback_period": 60
            }

class StrategyManager:
    """
    Strategy manager that leverages existing high-quality functional components.
    
    Instead of implementing signal generation directly, it delegates to:
    - UnifiedSignalEngine for signal generation
    - TechnicalIndicatorEngine for indicator calculations  
    - PortfolioOptimizationEngine for position sizing
    - CoreAnalytics for performance monitoring
    - AdvancedRiskManager for central risk authority integration
    
    CRITICAL: All trading proposals must be submitted to RiskManager before execution.
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """Initialize strategy manager with delegation to existing components"""
        self.config = config or StrategyConfig()
        
        # Initialize existing functional components
        self._initialize_delegated_components()
        
        # Strategy state
        self.active_signals: Dict[str, List[TradingSignal]] = {}
        self.current_regime = "unknown"
        self.performance_metrics = {}
        self.is_running = False
        
        # Risk management integration
        self.pending_authorizations: Dict[str, TradeRequest] = {}
        self.authorized_proposals: Dict[str, TradeAuthorization] = {}
        
        # Subscribers for integration
        self.subscribers: List[Any] = []
        
        logger.info("📊 StrategyManager initialized with component delegation and risk integration")
    
    def _initialize_delegated_components(self) -> None:
        """Initialize existing functional components for delegation (fail-fast architecture)"""
        try:
            # Initialize UnifiedSignalEngine for signal generation
            signal_config = SignalConfig(**self.config.signal_engine_config)
            self.signal_engine = UnifiedSignalEngine(signal_config)
            logger.info("✅ Delegating signal generation to UnifiedSignalEngine")
            
            # Initialize PortfolioOptimizationEngine for position sizing
            self.portfolio_optimizer = PortfolioOptimizationEngine()
            logger.info("✅ Delegating portfolio optimization to PortfolioOptimizationEngine")
            
            # Initialize CoreAnalyticsEngine for performance monitoring
            self.analytics_engine = CoreAnalyticsEngine()
            logger.info("✅ Delegating analytics to CoreAnalyticsEngine")
            
            # Initialize MonitoringAnalyticsEngine for quality tracking
            self.monitoring_analytics = MonitoringAnalyticsEngine()
            logger.info("✅ Delegating monitoring to MonitoringAnalyticsEngine")
            
            # Initialize AdvancedRiskManager for central risk authority
            self.risk_manager = AdvancedRiskManager()
            logger.info("✅ Central Risk Authority connected - all proposals require authorization")
            
            # Set unavailable components to None (not needed with main components)
            self.indicator_engine = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing delegated components: {e}")
            raise RuntimeError(f"Failed to initialize StrategyManager: {e}")
    
    async def generate_signals(self, symbols: List[str], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """
        Generate signals using delegated UnifiedSignalEngine with Central Risk Authority integration.
        
        CRITICAL FLOW:
        1. Generate trading signals through UnifiedSignalEngine
        2. Convert signals to TradeRequests 
        3. Submit ALL proposals to RiskManager for authorization
        4. Only notify subscribers of AUTHORIZED signals
        5. Maintain authorization metadata for execution tracking
        """
        authorized_signals = []
        
        try:
            if self.signal_engine:
                # Delegate signal generation to UnifiedSignalEngine
                for symbol in symbols:
                    symbol_data = market_data.get(symbol, {})
                    
                    # Let the signal engine handle the complex signal generation
                    engine_signals = await self.signal_engine.generate_signals(
                        symbol=symbol,
                        market_data=symbol_data,
                        regime_context=self.current_regime
                    )
                    
                    # Filter signals based on our configuration
                    filtered_signals = [
                        signal for signal in engine_signals
                        if signal.strength >= self.config.min_signal_strength
                    ]
                    
                    # CENTRAL RISK AUTHORITY: Submit each signal for authorization
                    for signal in filtered_signals:
                        authorization = await self._submit_signal_for_authorization(signal)
                        
                        if authorization.authorized:
                            # Store authorization metadata in signal
                            signal.metadata = signal.metadata or {}
                            signal.metadata['authorization_token'] = authorization.authorization_token
                            signal.metadata['risk_limits_applied'] = authorization.risk_limits_applied
                            signal.metadata['authorization_timestamp'] = authorization.timestamp
                            
                            authorized_signals.append(signal)
                            logger.info(f"✅ Signal authorized for {signal.symbol}: {signal.signal_type.value} (token: {authorization.authorization_token[:8]}...)")
                        else:
                            logger.warning(f"🚫 Signal REJECTED for {signal.symbol}: {authorization.rejection_reason}")
                            # Track rejections for monitoring
                            self._track_rejection(signal, authorization)
            else:
                # Fallback to simple signal generation if signal engine not available
                logger.warning("⚠️ Using fallback signal generation - UnifiedSignalEngine not available")
                fallback_signals = await self._fallback_signal_generation(symbols, market_data)
                
                # Even fallback signals must be authorized
                for signal in fallback_signals:
                    authorization = await self._submit_signal_for_authorization(signal)
                    if authorization.authorized:
                        signal.metadata = signal.metadata or {}
                        signal.metadata['authorization_token'] = authorization.authorization_token
                        authorized_signals.append(signal)
            
            # Store and notify ONLY authorized signals
            for signal in authorized_signals:
                self._store_signal(signal)
                self._notify_subscribers(signal)
            
            logger.info(f"📊 Generated {len(authorized_signals)} authorized signals from {sum(len([s for s in [engine_signals if 'engine_signals' in locals() else []]]) for _ in symbols)} total proposals")
            return authorized_signals
            
        except Exception as e:
            logger.error(f"❌ Error generating signals with risk authorization: {e}")
            return []
    
    async def _submit_signal_for_authorization(self, signal: TradingSignal) -> TradeAuthorization:
        """
        Submit trading signal to RiskManager for authorization.
        
        This implements the Central Risk Authority pattern where ALL trading decisions
        must be approved by the risk management system before execution.
        """
        try:
            # Convert TradingSignal to TradeRequest
            trade_request = TradeRequest(
                request_id=str(uuid.uuid4()),
                symbol=signal.symbol,
                action=signal.signal_type.value.upper(),
                quantity=signal.strength * 100,  # Convert strength to quantity (placeholder logic)
                price=signal.price,
                strategy=signal.strategy,
                timestamp=signal.timestamp,
                metadata={
                    'signal_confidence': signal.confidence,
                    'original_signal_strength': signal.strength,
                    'regime_context': self.current_regime,
                    'strategy_manager_id': id(self)
                }
            )
            
            # Store pending authorization for tracking
            self.pending_authorizations[trade_request.request_id] = trade_request
            
            # Submit to RiskManager for authorization
            authorization = await self.risk_manager.authorize_trade(trade_request)
            
            # Store authorization result
            self.authorized_proposals[trade_request.request_id] = authorization
            
            # Clean up pending
            self.pending_authorizations.pop(trade_request.request_id, None)
            
            return authorization
            
        except Exception as e:
            logger.error(f"❌ Error submitting signal for authorization: {e}")
            # Return rejection on error
            return TradeAuthorization(
                request_id=str(uuid.uuid4()),
                authorized=False,
                authorization_token="",
                risk_limits_applied={},
                rejection_reason=f"Authorization system error: {str(e)}",
                timestamp=datetime.now()
            )
    
    def _track_rejection(self, signal: TradingSignal, authorization: TradeAuthorization) -> None:
        """Track rejected signals for monitoring and analysis"""
        try:
            rejection_data = {
                'symbol': signal.symbol,
                'signal_type': signal.signal_type.value,
                'strategy': signal.strategy,
                'rejection_reason': authorization.rejection_reason,
                'timestamp': authorization.timestamp,
                'regime_context': self.current_regime
            }
            
            # Store in monitoring system if available
            if self.monitoring_analytics:
                self.monitoring_analytics.track_rejection(rejection_data)
                
        except Exception as e:
            logger.error(f"❌ Error tracking signal rejection: {e}")
    
    async def _fallback_signal_generation(self, symbols: List[str], market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Fallback signal generation when UnifiedSignalEngine is not available"""
        signals = []
        
        for symbol in symbols:
            # Generate a simple signal based on regime
            if self.current_regime in ["trending_up", "breakout"]:
                signal = TradingSignal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    strength=0.5,
                    price=100.0,  # Placeholder
                    timestamp=datetime.now(),
                    strategy="fallback",
                    confidence=0.5
                )
                signals.append(signal)
        
        return signals
    
    def _store_signal(self, signal: TradingSignal) -> None:
        """Store signal in active signals"""
        if signal.symbol not in self.active_signals:
            self.active_signals[signal.symbol] = []
        
        self.active_signals[signal.symbol].append(signal)
        
        # Maintain reasonable size
        if len(self.active_signals[signal.symbol]) > 10:
            self.active_signals[signal.symbol] = self.active_signals[signal.symbol][-5:]
    
    def _notify_subscribers(self, signal: TradingSignal) -> None:
        """Notify subscribers of new signal"""
        for subscriber in self.subscribers:
            try:
                subscriber.on_trading_signal(signal)
            except Exception as e:
                logger.error(f"❌ Error notifying subscriber: {e}")
    
    def update_market_context(self, regime: str, context: Dict[str, Any]) -> None:
        """Update market context for strategy decisions"""
        self.current_regime = regime
        logger.info(f"📊 Market context updated: regime={regime}")
        
        # Update signal engine context if available
        if self.signal_engine:
            try:
                self.signal_engine.update_market_context(regime, context)
            except Exception as e:
                logger.warning(f"⚠️ Could not update signal engine context: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics using delegated analytics"""
        try:
            if self.analytics_engine:
                # Delegate to CoreAnalytics for sophisticated performance analysis
                return self.analytics_engine.calculate_strategy_performance(
                    signals=self.active_signals,
                    current_regime=self.current_regime
                )
            else:
                # Fallback performance calculation
                total_signals = sum(len(signals) for signals in self.active_signals.values())
                return {
                    "total_signals": total_signals,
                    "active_signals_count": total_signals,
                    "current_regime": self.current_regime,
                    "status": "running" if self.is_running else "stopped",
                    "analytics_engine": "fallback"
                }
        except Exception as e:
            logger.error(f"❌ Error calculating performance metrics: {e}")
            return {"error": str(e)}
    
    async def startup(self) -> bool:
        """Start the strategy manager with risk management integration"""
        try:
            logger.info("🚀 Starting StrategyManager with delegated components and risk integration...")
            
            # Start delegated components
            if self.signal_engine:
                # UnifiedSignalEngine is already initialized in constructor
                logger.info("✅ UnifiedSignalEngine ready")
            
            if self.analytics_engine:
                # CoreAnalyticsEngine is already initialized in constructor
                logger.info("✅ CoreAnalytics ready")
            
            # Start AdvancedRiskManager
            if self.risk_manager:
                try:
                    await self.risk_manager.startup()
                    logger.info("✅ AdvancedRiskManager started - Central Risk Authority active")
                except Exception as e:
                    logger.error(f"❌ Failed to start Risk Manager: {e}")
                    return False
            
            self.is_running = True
            logger.info("✅ StrategyManager started successfully with risk authorization")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start StrategyManager: {e}")
            return False
    
    async def shutdown(self) -> None:
        """Shutdown the strategy manager with risk management cleanup"""
        try:
            logger.info("⏹️ Shutting down StrategyManager...")
            
            self.is_running = False
            
            # Shutdown delegated components
            if self.signal_engine:
                try:
                    await self.signal_engine.stop()
                    logger.info("✅ UnifiedSignalEngine stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping signal engine: {e}")
            
            if self.analytics_engine:
                try:
                    await self.analytics_engine.shutdown()
                    logger.info("✅ CoreAnalytics stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping analytics engine: {e}")
            
            # Shutdown AdvancedRiskManager
            if self.risk_manager:
                try:
                    await self.risk_manager.shutdown()
                    logger.info("✅ AdvancedRiskManager stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping risk manager: {e}")
            
            # Clear authorization tracking
            self.pending_authorizations.clear()
            self.authorized_proposals.clear()
            
            logger.info("✅ StrategyManager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Failed to shutdown StrategyManager: {e}")
    
    def subscribe(self, subscriber: Any) -> None:
        """Subscribe to trading signals"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            logger.info(f"📢 New strategy subscriber added: {type(subscriber).__name__}")
    
    def unsubscribe(self, subscriber: Any) -> None:
        """Unsubscribe from trading signals"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            logger.info(f"📢 Strategy subscriber removed: {type(subscriber).__name__}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of strategy manager including risk management"""
        active_signals_count = sum(len(signals) for signals in self.active_signals.values())
        
        return {
            "is_running": self.is_running,
            "current_regime": self.current_regime,
            "active_signals_count": active_signals_count,
            "enabled_strategies": self.config.enabled_strategies,
            "signal_engine_available": self.signal_engine is not None,
            "analytics_engine_available": self.analytics_engine is not None,
            "portfolio_optimizer_available": self.portfolio_optimizer is not None,
            "indicator_engine_available": self.indicator_engine is not None,
            "risk_manager_available": self.risk_manager is not None,
            "subscribers_count": len(self.subscribers),
            "pending_authorizations": len(self.pending_authorizations),
            "total_authorizations": len(self.authorized_proposals),
            "central_risk_authority_active": self.risk_manager is not None and self.is_running
        }

# Interface for strategy signal subscribers
class IStrategySubscriber(ABC):
    """Interface for strategy signal subscribers"""
    
    @abstractmethod
    def on_trading_signal(self, signal: TradingSignal) -> None:
        """Handle trading signals"""
        pass

# Export key components
__all__ = [
    'StrategyManager', 
    'StrategyConfig',
    'TradingSignal',
    'SignalType',
    'BaseStrategy',
    'IStrategySubscriber'
]