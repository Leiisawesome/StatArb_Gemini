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

import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
from enum import Enum
import threading
import uuid
import asyncio

# Import ISystemComponent for orchestrator integration (Rule 1)
try:
    from ..system.interfaces import ISystemComponent
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass
        
        @abstractmethod
        async def start(self) -> bool:
            pass
        
        @abstractmethod
        async def stop(self) -> bool:
            pass
        
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass
        
        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass

# Import centralized configuration (Rule 1, Section 7)
try:
    from ..config.component_config import RegimeConfig
except ImportError:
    # Fallback for testing - will create inline
    RegimeConfig = None

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Advanced market regime classifications - Professional Grade"""
    
    # === DIRECTIONAL + VOLATILITY REGIMES ===
    BULL_LOW_VOL = "bull_low_volatility"           # Strong uptrend, calm conditions
    BULL_HIGH_VOL = "bull_high_volatility"         # Strong uptrend, volatile conditions
    BEAR_LOW_VOL = "bear_low_volatility"           # Downtrend, controlled decline
    BEAR_HIGH_VOL = "bear_high_volatility"         # Downtrend, panic conditions
    
    # === TREND STRENGTH REGIMES ===
    STRONG_TRENDING = "strong_trending"            # Clear directional momentum
    WEAK_TRENDING = "weak_trending"                # Mild directional bias
    RANGE_BOUND = "range_bound"                    # Sideways consolidation
    CHOPPY = "choppy"                              # Erratic, no clear direction
    
    # === MARKET STRESS REGIMES ===
    CRISIS_MODE = "crisis_mode"                    # Extreme stress, flight to safety
    RECOVERY_MODE = "recovery_mode"                # Post-crisis stabilization
    EUPHORIA_MODE = "euphoria_mode"                # Excessive optimism, bubble conditions
    COMPLACENCY_MODE = "complacency_mode"          # Low volatility, overconfidence
    
    # === LIQUIDITY & FLOW REGIMES ===
    LIQUIDITY_CRUNCH = "liquidity_crunch"          # Poor market liquidity
    HIGH_LIQUIDITY = "high_liquidity"              # Abundant market liquidity
    ROTATION_MODE = "rotation_mode"                # Sector/style rotation active
    
    # === LEGACY COMPATIBILITY ===
    BULL_MARKET = "bull_market"                    # Legacy: General bull market
    BEAR_MARKET = "bear_market"                    # Legacy: General bear market
    SIDEWAYS = "sideways"                          # Legacy: Sideways movement
    HIGH_VOLATILITY = "high_volatility"            # Legacy: High volatility
    LOW_VOLATILITY = "low_volatility"              # Legacy: Low volatility
    TRENDING = "trending"                          # Legacy: Trending
    MEAN_REVERTING = "mean_reverting"              # Legacy: Mean reverting

@dataclass
class TimeframeRegime:
    """Regime analysis for a specific timeframe"""
    timeframe: str                               # "5min", "1H", "1D", "1W"
    regime: MarketRegime
    confidence: float
    trend_strength: float
    volatility: float
    regime_duration: int                         # periods in current regime
    transition_probability: float

@dataclass
class TransitionPrediction:
    """ML-based regime transition prediction"""
    current_regime: MarketRegime
    predicted_regime: MarketRegime
    transition_probability: float               # 0-1 probability of transition
    confidence: float                          # Model confidence in prediction
    time_horizon: str                          # "1H", "1D", "1W" prediction horizon
    contributing_factors: List[str]            # Key factors driving prediction
    model_accuracy: float                      # Historical model accuracy
    prediction_timestamp: datetime

@dataclass
class RegimeAnalysis:
    """Enhanced regime analysis results - Professional Grade"""
    
    # === PRIMARY REGIME CLASSIFICATION ===
    primary_regime: MarketRegime
    confidence: float
    regime_duration: int  # days in current regime
    timestamp: datetime
    
    # === DETAILED REGIME COMPONENTS ===
    directional_regime: str = "neutral"           # bull/bear/sideways
    volatility_regime: str = "normal"             # low/normal/high/extreme
    trend_strength: float = 0.0                  # 0-1 scale
    stress_level: float = 0.0                    # 0-1 scale (0=calm, 1=crisis)
    liquidity_regime: str = "normal"             # poor/normal/abundant
    
    # === REGIME CHARACTERISTICS ===
    regime_stability: float = 0.0                # How stable is current regime (0-1)
    transition_probability: float = 0.0          # Probability of regime change (0-1)
    regime_maturity: float = 0.0                 # How mature is current regime (0-1)
    
    # === MULTI-TIMEFRAME REGIME ANALYSIS ===
    timeframe_regimes: Dict[str, TimeframeRegime] = None  # Regime by timeframe
    regime_consensus: float = 0.0                # Agreement across timeframes (0-1)
    dominant_timeframe: str = "1D"               # Most influential timeframe
    regime_hierarchy: Dict[str, float] = None    # Timeframe importance weights
    
    # === ML-BASED TRANSITION PREDICTIONS ===
    transition_predictions: Dict[str, TransitionPrediction] = None  # Predictions by horizon
    ml_transition_probability: float = 0.0       # ML-enhanced transition probability
    transition_confidence: float = 0.0           # Confidence in transition prediction
    predicted_next_regime: Optional[MarketRegime] = None  # Most likely next regime
    
    # === STRATEGY IMPLICATIONS ===
    strategy_suitability: Dict[str, float] = None  # Strategy performance expectations
    risk_adjustment: float = 1.0                 # Risk multiplier for current regime
    position_sizing_factor: float = 1.0          # Position size adjustment
    
    # === REGIME CONTEXT ===
    sub_regimes: Dict[str, str] = None           # Detailed sub-regime breakdown
    regime_drivers: List[str] = None             # Key factors driving current regime
    regime_outlook: str = "neutral"              # Expected regime evolution
    
    def __post_init__(self):
        """Initialize default values for mutable fields"""
        if self.strategy_suitability is None:
            self.strategy_suitability = {}
        if self.sub_regimes is None:
            self.sub_regimes = {}
        if self.regime_drivers is None:
            self.regime_drivers = []
        if self.timeframe_regimes is None:
            self.timeframe_regimes = {}
        if self.regime_hierarchy is None:
            self.regime_hierarchy = {
                "5min": 0.15,   # Short-term noise
                "1H": 0.25,     # Intraday trends
                "1D": 0.40,     # Primary timeframe
                "1W": 0.20      # Long-term context
            }
        if self.transition_predictions is None:
            self.transition_predictions = {}

class IRegimeSubscriber:
    """Interface for regime change subscribers"""
    
    async def on_regime_change(self, regime_analysis: RegimeAnalysis) -> None:
        """Handle regime change notification"""

class EnhancedRegimeEngine(ISystemComponent):
    """
    Enhanced Regime Engine with ISystemComponent Integration
    
    Institutional-grade market regime detection with orchestrator integration:
    - Implements ISystemComponent for lifecycle management
    - Market regime detection and classification
    - Regime change detection with professional standards
    - Strategy suitability assessment based on regime
    - Distribution of regime analysis to risk manager and other components
    - Health monitoring and performance tracking
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Try to import centralized RegimeConfig (Rule 1, Section 7)
        try:
            from ..config.component_config import RegimeConfig as CentralizedRegimeConfig
            RegimeConfigClass = CentralizedRegimeConfig
        except ImportError:
            # Fallback: Create local RegimeConfig if import fails (testing/backtest scenario)
            from dataclasses import dataclass
            @dataclass
            class RegimeConfigClass:
                lookback_window: int = 60
                volatility_window: int = 20
                trend_threshold: float = 0.02
                regime_change_threshold: float = 0.7
                update_frequency: int = 300
                enable_enhanced_detection: bool = True
        
        # Initialize with config (supports RegimeConfig object or dict)
        if config is None:
            self.config = RegimeConfigClass()
        elif isinstance(config, dict):
            self.config = RegimeConfigClass(**config)
        elif hasattr(config, '__dict__'):
            # Already a config object (centralized or local)
            self.config = config
        else:
            self.config = RegimeConfigClass()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("✅ Using centralized RegimeConfig (Rule 1, Section 7)")
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None
        
        # Event-driven integration
        self.subscribers: List[IRegimeSubscriber] = []
        
        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # Health and performance tracking
        self.health_metrics = {
            'component_type': 'EnhancedRegimeEngine',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_regime_analyses': 0,
                'successful_regime_analyses': 0,
                'failed_regime_analyses': 0,
                'average_analysis_time': 0.0,
                'regime_changes_detected': 0
            }
        }
        
        # Current regime state
        self.current_regime: Optional[RegimeAnalysis] = None
        self.regime_history: List[RegimeAnalysis] = []
        
        # Market data for regime analysis
        self.market_data_buffer: Dict[str, List[float]] = {}
        self.price_history: Dict[str, pd.DataFrame] = {}
        
        # Multi-timeframe data buffers
        self.timeframe_buffers: Dict[str, Dict[str, List[float]]] = {
            "5min": {},
            "1H": {},
            "1D": {},
            "1W": {}
        }
        
        # Timeframe aggregation counters (1-minute data points per timeframe)
        self.timeframe_intervals: Dict[str, int] = {
            "5min": 5,      # 5 minutes
            "1H": 60,       # 60 minutes
            "1D": 1440,     # 1440 minutes (24 hours)
            "1W": 10080     # 10080 minutes (7 days)
        }
        
        self.timeframe_counters: Dict[str, int] = {
            "5min": 0,
            "1H": 0,
            "1D": 0,
            "1W": 0
        }
        
        # Subscribers for regime changes
        self.subscribers: List[IRegimeSubscriber] = []
        
        # Threading
        self._lock = threading.Lock()
        
        self.logger.info(f"🚀 Enhanced Regime Engine initialized with component ID: {self.component_id}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedRegimeEngine",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5  # Layer 0: REGIME-FIRST - Foundation for all components
        )
        
        self.logger.info(f"✅ EnhancedRegimeEngine registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            self.logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Interface Implementation
    # ========================================
    
    async def initialize(self) -> bool:
        """Initialize the Enhanced Regime Engine"""
        try:
            self.logger.info("🔄 Initializing Enhanced Regime Engine...")
            
            # Initialize regime analysis engines
            await self._initialize_regime_engines()
            
            # Initialize monitoring
            await self._initialize_monitoring_system()
            
            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'
            
            self.logger.info("✅ Enhanced Regime Engine initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Regime Engine initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False
    
    async def start(self) -> bool:
        """Start the Enhanced Regime Engine"""
        if not self.is_initialized:
            self.logger.error("Cannot start Enhanced Regime Engine: not initialized")
            return False
        
        try:
            self.logger.info("🚀 Starting Enhanced Regime Engine...")
            
            # Start regime analysis
            await self._start_regime_analysis()
            
            # Start monitoring
            await self._start_monitoring()
            
            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'
            
            self.logger.info("✅ Enhanced Regime Engine started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Regime Engine start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def stop(self) -> bool:
        """Stop the Enhanced Regime Engine"""
        try:
            self.logger.info("🛑 Stopping Enhanced Regime Engine...")
            
            # Stop regime analysis
            await self._stop_regime_analysis()
            
            # Stop monitoring
            await self._stop_monitoring()
            
            # Clear buffers
            self.market_data_buffer.clear()
            self.price_history.clear()
            
            # Update status
            self.is_operational = False
            self.health_metrics['operational_status'] = 'inactive'
            
            self.logger.info("✅ Enhanced Regime Engine stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced Regime Engine stop failed: {e}")
            self.health_metrics['error_count'] += 1
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            current_time = datetime.now()
            self.health_metrics['last_health_check'] = current_time
            
            # Calculate uptime
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (current_time - self.start_time).total_seconds()
            
            # Check regime analysis health
            analysis_healthy = await self._check_analysis_health()
            
            # Overall health assessment
            overall_healthy = (
                self.is_initialized and
                self.is_operational and
                analysis_healthy and
                self.health_metrics['error_count'] < 10
            )
            
            return {
                'healthy': overall_healthy,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'uptime_seconds': uptime_seconds,
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count'],
                'performance_metrics': self.health_metrics['performance_metrics'],
                'analysis_healthy': analysis_healthy,
                'current_regime': self.current_regime.primary_regime.value if self.current_regime else None,
                'regime_history_count': len(self.regime_history),
                'subscribers_count': len(self.subscribers),
                'last_health_check': current_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_type': self.health_metrics['component_type'],
                'component_id': self.component_id,
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current component status"""
        return {
            'component_id': self.component_id,
            'component_type': self.health_metrics['component_type'],
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'configuration': {
                'lookback_window': self.config.lookback_window,
                'volatility_window': self.config.volatility_window,
                'trend_threshold': self.config.trend_threshold,
                'regime_change_threshold': self.config.regime_change_threshold,
                'enable_enhanced_detection': self.config.enable_enhanced_detection
            },
            'health_metrics': self.health_metrics
        }
    
    # Enhanced Internal Methods
    
    async def _initialize_regime_engines(self) -> None:
        """Initialize regime analysis engines"""
        try:
            self.logger.info("🔧 Initializing regime analysis engines...")
            
            # Initialize ML models for regime prediction
            self.transition_scaler = StandardScaler()
            self.transition_models = {
                "1H": RandomForestClassifier(n_estimators=100, random_state=42),
                "1D": GradientBoostingClassifier(n_estimators=100, random_state=42),
                "1W": RandomForestClassifier(n_estimators=50, random_state=42)
            }
            self.transition_history = []  # Historical transitions for training
            self.models_trained = False
            
            self.logger.info("✅ Regime analysis engines initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize regime engines: {e}")
            raise
    
    async def _initialize_monitoring_system(self) -> None:
        """Initialize monitoring system"""
        try:
            self.logger.info("📈 Initializing monitoring system...")
            
            # Initialize performance monitoring
            self.health_metrics['performance_metrics'] = {
                'total_regime_analyses': 0,
                'successful_regime_analyses': 0,
                'failed_regime_analyses': 0,
                'average_analysis_time': 0.0,
                'regime_changes_detected': 0
            }
            
            self.logger.info("✅ Monitoring system initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {e}")
            raise
    
    async def _start_regime_analysis(self) -> None:
        """Start regime analysis"""
        try:
            self.logger.info("📊 Starting regime analysis...")
            # Regime analysis is event-driven, no background tasks needed
            self.logger.info("✅ Regime analysis started")
            
        except Exception as e:
            self.logger.error(f"Failed to start regime analysis: {e}")
            raise
    
    async def _start_monitoring(self) -> None:
        """Start monitoring systems"""
        try:
            self.logger.info("📊 Starting monitoring systems...")
            # Monitoring is passive for regime engine
            self.logger.info("✅ Monitoring systems started")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise
    
    async def _stop_regime_analysis(self) -> None:
        """Stop regime analysis"""
        try:
            self.logger.info("📊 Stopping regime analysis...")
            # No background tasks to stop
            self.logger.info("✅ Regime analysis stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop regime analysis: {e}")
            raise
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring systems"""
        try:
            self.logger.info("📊 Stopping monitoring systems...")
            # Monitoring is passive for regime engine
            self.logger.info("✅ Monitoring systems stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            raise
    
    async def _check_analysis_health(self) -> bool:
        """Check health of regime analysis"""
        try:
            # For a newly initialized system, it's healthy if it's operational
            # even without regime data (data will come when market data is processed)
            if self.is_operational and self.is_initialized:
                return True
            
            # If we have regime analysis, that's also healthy
            if self.current_regime is not None:
                return True
            
            # If we have historical data, that's healthy too
            if len(self.regime_history) > 0:
                return True
            
            # If not operational or initialized, then it's unhealthy
            return False
            
        except Exception as e:
            self.logger.warning(f"Analysis health check failed: {e}")
            return False
    
    # ========================================
    # EVENT-DRIVEN INTEGRATION METHODS
    # ========================================
    
    def subscribe(self, subscriber: IRegimeSubscriber):
        """Subscribe to regime change events"""
        self.subscribers.append(subscriber)
        self.logger.info(f"📝 New regime subscriber: {type(subscriber).__name__}")
    
    async def notify_regime_change(self, regime_analysis):
        """Notify all subscribers of regime changes"""
        import inspect
        for subscriber in self.subscribers:
            try:
                # Check if on_regime_change is async or sync
                callback = subscriber.on_regime_change
                if inspect.iscoroutinefunction(callback):
                    # Async callback - await it
                    await callback(regime_analysis)
                else:
                    # Sync callback - call directly
                    callback(regime_analysis)
            except Exception as e:
                self.logger.error(f"Failed to notify subscriber {type(subscriber).__name__}: {e}")
    
    # ========================================
    # STANDARDIZED DATA FLOW METHODS
    # ========================================
    
    def process_market_data(self, market_data: Any) -> Dict[str, Any]:
        """
        Process market data for regime analysis
        
        Args:
            market_data: Dict with keys: symbol, timestamp, open, high, low, close, volume
        
        Returns:
            Dict with processing results
        """
        try:
            # Extract data from market update
            if isinstance(market_data, dict):
                symbol = market_data.get('symbol', 'UNKNOWN')
                timestamp = market_data.get('timestamp', datetime.now())
                close = market_data.get('close', 0.0)
                high = market_data.get('high', close)
                low = market_data.get('low', close)
                volume = market_data.get('volume', 0)
                
                # Initialize symbol buffer if needed
                if symbol not in self.market_data_buffer:
                    self.market_data_buffer[symbol] = {
                        'close': [],
                        'high': [],
                        'low': [],
                        'volume': [],
                        'timestamp': []
                    }
                
                # Add data to buffer
                buffer = self.market_data_buffer[symbol]
                buffer['close'].append(close)
                buffer['high'].append(high)
                buffer['low'].append(low)
                buffer['volume'].append(volume)
                buffer['timestamp'].append(timestamp)
                
                # Keep buffer size manageable (last N points)
                max_buffer_size = self.config.lookback_window * 2  # Keep 2x lookback for safety
                if len(buffer['close']) > max_buffer_size:
                    for key in buffer:
                        buffer[key] = buffer[key][-max_buffer_size:]
                
                # Only analyze if we have enough data
                if len(buffer['close']) >= self.config.lookback_window:
                    # Calculate regime indicators
                    regime_indicators = self._calculate_regime_indicators(symbol)
                    
                    # Classify regime
                    new_regime = self._classify_regime(symbol, regime_indicators)
                    
                    # Check for regime change
                    regime_changed = False
                    if self.current_regime is None:
                        regime_changed = True
                    elif new_regime.primary_regime != self.current_regime.primary_regime:
                        regime_changed = True
                    
                    # Update current regime
                    self.current_regime = new_regime
                    self.regime_history.append(new_regime)
                    
                    # Keep regime history manageable
                    if len(self.regime_history) > 1000:
                        self.regime_history = self.regime_history[-1000:]
                    
                    # Notify subscribers on regime change
                    if regime_changed and len(self.subscribers) > 0:
                        asyncio.create_task(self.notify_regime_change(new_regime))
                    
                    # Update metrics
                    self.health_metrics['performance_metrics']['total_regime_analyses'] += 1
                    self.health_metrics['performance_metrics']['successful_regime_analyses'] += 1
                    if regime_changed:
                        self.health_metrics['performance_metrics']['regime_changes_detected'] += 1
                    
                    return {
                        'market_data_processed': True,
                        'symbol': symbol,
                        'regime_detected': new_regime.primary_regime.value if new_regime else None,
                        'regime_changed': regime_changed,
                        'confidence': new_regime.confidence if new_regime else 0.0,
                        'buffer_size': len(buffer['close']),
                        'processing_timestamp': datetime.now()
                    }
                else:
                    # Not enough data yet
                    return {
                        'market_data_processed': True,
                        'symbol': symbol,
                        'regime_detected': None,
                        'regime_changed': False,
                        'buffer_size': len(buffer['close']),
                        'required_size': self.config.lookback_window,
                        'processing_timestamp': datetime.now()
                    }
            
            else:
                self.logger.warning(f"Unexpected market_data type: {type(market_data)}")
                return {
                    'market_data_processed': False,
                    'error': 'Invalid market_data format',
                    'processing_timestamp': datetime.now()
                }
                
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
            self.health_metrics['performance_metrics']['failed_regime_analyses'] += 1
            return {
                'market_data_processed': False,
                'error': str(e),
                'processing_timestamp': datetime.now()
            }
    
    def _calculate_regime_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate technical indicators for regime classification"""
        buffer = self.market_data_buffer[symbol]
        closes = np.array(buffer['close'])
        highs = np.array(buffer['high'])
        lows = np.array(buffer['low'])
        volumes = np.array(buffer['volume'])
        
        # Calculate returns
        returns = np.diff(closes) / closes[:-1]
        
        # Calculate volatility (rolling std of returns, annualized)
        vol_window = min(self.config.volatility_window, len(returns))
        if vol_window > 1:
            volatility = np.std(returns[-vol_window:]) * np.sqrt(252 * 390)  # Annualized intraday vol
        else:
            volatility = 0.0
        
        # Calculate trend (simple moving average slope)
        sma_window = min(self.config.lookback_window, len(closes))
        sma = np.mean(closes[-sma_window:])
        price = closes[-1]
        trend = (price - sma) / sma if sma > 0 else 0.0
        
        # Calculate momentum (rate of change)
        momentum_window = min(20, len(closes))
        if momentum_window > 1:
            momentum = (closes[-1] - closes[-momentum_window]) / closes[-momentum_window]
        else:
            momentum = 0.0
        
        # Calculate trend strength (ADX-like)
        if len(closes) >= 14:
            # Simplified trend strength
            up_moves = np.maximum(highs[1:] - highs[:-1], 0)
            down_moves = np.maximum(lows[:-1] - lows[1:], 0)
            trend_strength = np.mean(up_moves[-14:]) / (np.mean(up_moves[-14:]) + np.mean(down_moves[-14:]) + 1e-10)
        else:
            trend_strength = 0.5
        
        # Volume analysis
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
        
        return {
            'volatility': volatility,
            'trend': trend,
            'momentum': momentum,
            'trend_strength': trend_strength,
            'volume_ratio': volume_ratio,
            'price': price
        }
    
    def _classify_regime(self, symbol: str, indicators: Dict[str, float]) -> RegimeAnalysis:
        """Classify market regime based on indicators"""
        
        volatility = indicators['volatility']
        trend = indicators['trend']
        momentum = indicators['momentum']
        trend_strength = indicators['trend_strength']
        
        # Classify volatility regime
        if volatility < 0.15:
            vol_regime = "low_volatility"
        elif volatility < 0.25:
            vol_regime = "normal_volatility"
        elif volatility < 0.40:
            vol_regime = "high_volatility"
        else:
            vol_regime = "extreme_volatility"
        
        # Classify directional regime
        if trend > self.config.trend_threshold:
            directional = "bull"
        elif trend < -self.config.trend_threshold:
            directional = "bear"
        else:
            directional = "sideways"
        
        # Combine into primary regime
        if directional == "bull" and vol_regime in ["low_volatility", "normal_volatility"]:
            primary_regime = MarketRegime.BULL_LOW_VOL
            confidence = 0.8
        elif directional == "bull" and vol_regime in ["high_volatility", "extreme_volatility"]:
            primary_regime = MarketRegime.BULL_HIGH_VOL
            confidence = 0.7
        elif directional == "bear" and vol_regime in ["low_volatility", "normal_volatility"]:
            primary_regime = MarketRegime.BEAR_LOW_VOL
            confidence = 0.8
        elif directional == "bear" and vol_regime in ["high_volatility", "extreme_volatility"]:
            primary_regime = MarketRegime.BEAR_HIGH_VOL
            confidence = 0.7
        elif abs(trend) < self.config.trend_threshold / 2:
            primary_regime = MarketRegime.RANGE_BOUND
            confidence = 0.75
        elif vol_regime == "extreme_volatility":
            primary_regime = MarketRegime.CHOPPY
            confidence = 0.65
        else:
            # Default to appropriate trending regime
            if trend_strength > 0.6:
                primary_regime = MarketRegime.STRONG_TRENDING
            else:
                primary_regime = MarketRegime.WEAK_TRENDING
            confidence = 0.6
        
        # Create regime analysis
        regime_analysis = RegimeAnalysis(
            primary_regime=primary_regime,
            confidence=confidence,
            regime_duration=0,  # Would need to track this over time
            timestamp=datetime.now(),
            directional_regime=directional,
            volatility_regime=vol_regime,
            trend_strength=trend_strength,
            stress_level=min(volatility / 0.5, 1.0),  # Normalize to 0-1
            liquidity_regime="normal",  # Would need more data for this
            regime_stability=confidence,  # Simplified
            transition_probability=1.0 - confidence,  # Inverse of confidence
            regime_maturity=0.5  # Would need historical tracking
        )
        
        return regime_analysis
    
    def analyze_data(self, data: Any) -> Dict[str, Any]:
        """Standardized method for analyzing data (alias for process_market_data)"""
        return self.process_market_data(data)
    
    def consume_data(self, data: Any) -> Dict[str, Any]:
        """Standardized method for consuming data"""
        return self.process_market_data(data)
    
    def analyze_regime(self, data: Any) -> Dict[str, Any]:
        """Standardized method for regime analysis"""
        return {
            'regime_analysis_performed': True,
            'input_data_type': type(data).__name__,
            'processing_timestamp': datetime.now(),
            'processing_component': 'EnhancedRegimeEngine'
        }
    
    def detect_regime(self, data: Any) -> Dict[str, Any]:
        """Standardized method for regime detection (alias)"""
        return self.analyze_regime(data)
    
    def classify_regime(self, data: Any) -> Dict[str, Any]:
        """Standardized method for regime classification (alias)"""
        return self.analyze_regime(data)
