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
from datetime import datetime
from typing import Dict, List, Optional, Any
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from dataclasses import dataclass
from enum import Enum
import threading
import time
import uuid
from collections import defaultdict, deque

# Import ISystemComponent for orchestrator integration
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

# Leverage existing high-quality regime components
# Import regime types from core_engine
# from ..type_definitions.regime import RegimeState, RegimeConfig

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
        self.config = RegimeEngineConfig(**config) if config else RegimeEngineConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Component identification and lifecycle
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time = None
        
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
    
    # ISystemComponent Interface Implementation
    
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
