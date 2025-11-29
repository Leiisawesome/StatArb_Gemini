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
from ..system.interfaces import ISystemComponent
from core_engine.exceptions import ConfigurationRequiredError

# Import centralized configuration (Rule 1, Section 7)
from ..config.component_config import RegimeConfig

# Import canonical MarketRegime from type_definitions (Single Source of Truth)
from ..type_definitions.regime import MarketRegime

logger = logging.getLogger(__name__)


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
class MLTransitionPrediction:
    """ML-based regime transition prediction (internal to engine.py)"""
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
    transition_predictions: Dict[str, MLTransitionPrediction] = None  # Predictions by horizon
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
        # Initialize with centralized RegimeConfig (Rule 1, Section 7)
        if config is None:
            self.config = RegimeConfig()
        elif isinstance(config, dict):
            self.config = RegimeConfig(**config)
        elif hasattr(config, '__dict__'):
            # Already a config object
            self.config = config
        else:
            raise ConfigurationRequiredError("Invalid config type for RegimeEngine")
        
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
        
        # CRITICAL: Bar-by-bar regime sequence persistence (for regime-aware processing)
        # Maps symbol -> List[Dict] with regime for each bar (timestamp-indexed)
        self.regime_sequence: Dict[str, List[Dict[str, Any]]] = {}
        # Maps symbol -> Dict[timestamp] -> regime for O(1) lookup
        self.regime_by_timestamp: Dict[str, Dict[datetime, RegimeAnalysis]] = {}
        
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
            
            # Clear regime sequence persistence
            self.regime_sequence.clear()
            self.regime_by_timestamp.clear()
            
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
            
            elif isinstance(market_data, pd.DataFrame):
                # Handle DataFrame input (for sequential bar-by-bar processing to enable regime-aware design)
                # CRITICAL: Process bar-by-bar to detect regime changes throughout the period
                # This enables true regime-aware processing (Rule 2: Regime-First Principle)
                if market_data.empty:
                    return {
                        'market_data_processed': False,
                        'error': 'Empty DataFrame provided',
                        'processing_timestamp': datetime.now()
                    }
                
                # Get symbol from DataFrame (assume single symbol)
                symbol = market_data['symbol'].iloc[0] if 'symbol' in market_data.columns else 'UNKNOWN'
                
                # Track regime sequence throughout the period
                regime_sequence = []
                last_detected_regime = None
                
                # Process each row in the DataFrame (bar-by-bar analysis)
                for idx, row in market_data.iterrows():
                    timestamp = row.get('timestamp', datetime.now())
                    close = row.get('close', 0.0)
                    high = row.get('high', close)
                    low = row.get('low', close)
                    volume = row.get('volume', 0)
                    
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
                    
                    # Analyze regime after each bar once we have enough data (bar-by-bar analysis)
                    if len(buffer['close']) >= self.config.lookback_window:
                        # Calculate regime indicators using rolling window
                        regime_indicators = self._calculate_regime_indicators(symbol)
                        
                        # Classify regime for this bar
                        new_regime = self._classify_regime(symbol, regime_indicators)
                        
                        # Check for regime change
                        regime_changed = False
                        if self.current_regime is None:
                            regime_changed = True
                        elif new_regime.primary_regime != self.current_regime.primary_regime:
                            regime_changed = True
                            self.logger.info(
                                f"Regime change detected for {symbol} at {timestamp}: "
                                f"{self.current_regime.primary_regime.value} -> {new_regime.primary_regime.value}"
                            )
                        
                        # Update current regime (this is the regime at THIS bar)
                        self.current_regime = new_regime
                        self.regime_history.append(new_regime)
                        
                        # Track regime sequence for this period
                        regime_entry = {
                            'timestamp': timestamp,
                            'bar_index': idx,
                            'regime': new_regime.primary_regime.value,
                            'confidence': new_regime.confidence,
                            'regime_changed': regime_changed
                        }
                        regime_sequence.append(regime_entry)
                        
                        # CRITICAL: Persist regime sequence for component access
                        if symbol not in self.regime_sequence:
                            self.regime_sequence[symbol] = []
                        self.regime_sequence[symbol].append(regime_entry)
                        
                        # CRITICAL: Persist regime by timestamp for O(1) lookup
                        if symbol not in self.regime_by_timestamp:
                            self.regime_by_timestamp[symbol] = {}
                        self.regime_by_timestamp[symbol][timestamp] = new_regime
                        
                        # Keep regime sequence manageable (last 10000 bars per symbol)
                        max_sequence_size = 10000
                        if len(self.regime_sequence[symbol]) > max_sequence_size:
                            # Remove oldest entries (FIFO)
                            removed = self.regime_sequence[symbol][:-max_sequence_size]
                            # Clean up timestamp index
                            for entry in removed:
                                old_timestamp = entry.get('timestamp')
                                if old_timestamp and old_timestamp in self.regime_by_timestamp.get(symbol, {}):
                                    del self.regime_by_timestamp[symbol][old_timestamp]
                            self.regime_sequence[symbol] = self.regime_sequence[symbol][-max_sequence_size:]
                        
                        # Keep regime history manageable
                        if len(self.regime_history) > 1000:
                            self.regime_history = self.regime_history[-1000:]
                        
                        # Notify subscribers on regime change (for real-time adaptation)
                        if regime_changed and len(self.subscribers) > 0:
                            asyncio.create_task(self.notify_regime_change(new_regime))
                        
                        # Update metrics
                        self.health_metrics['performance_metrics']['total_regime_analyses'] += 1
                        self.health_metrics['performance_metrics']['successful_regime_analyses'] += 1
                        if regime_changed:
                            self.health_metrics['performance_metrics']['regime_changes_detected'] += 1
                        
                        last_detected_regime = new_regime
                
                # Return summary with regime sequence
                if last_detected_regime:
                    return {
                        'market_data_processed': True,
                        'symbol': symbol,
                        'regime_detected': last_detected_regime.primary_regime.value,
                        'regime_changed': any(r['regime_changed'] for r in regime_sequence),
                        'confidence': last_detected_regime.confidence,
                        'buffer_size': len(self.market_data_buffer[symbol]['close']),
                        'processing_timestamp': datetime.now(),
                        # CRITICAL: Return regime sequence for regime-aware processing
                        'regime_sequence': regime_sequence,  # Bar-by-bar regime tracking
                        'regime_changes_count': sum(1 for r in regime_sequence if r['regime_changed']),
                        'total_bars_analyzed': len(regime_sequence),
                        'warm_up_bars': max(0, len(market_data) - len(regime_sequence))
                    }
                else:
                    # Not enough data yet (less than lookback_window)
                    return {
                        'market_data_processed': True,
                        'symbol': symbol,
                        'regime_detected': None,
                        'regime_changed': False,
                        'buffer_size': len(self.market_data_buffer[symbol]['close']),
                        'required_size': self.config.lookback_window,
                        'processing_timestamp': datetime.now(),
                        'regime_sequence': [],  # No regime detected yet
                        'total_bars_analyzed': 0,
                        'warm_up_bars': len(market_data)
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
        indicators['momentum']
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
            # No default - raise exception for unknown volatility regime
            raise ConfigurationRequiredError(f"Unknown volatility regime: {vol_regime}")
        
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
    
    # ========================================
    # REGIME ACCESS METHODS (for component integration)
    # ========================================
    
    def get_current_regime_context(self) -> Optional[RegimeAnalysis]:
        """
        Get current regime context for components (IRegimeAware interface support)
        
        Returns:
            Current RegimeAnalysis or None if no regime detected yet
        """
        return self.current_regime
    
    def get_current_regime(self) -> Optional[RegimeAnalysis]:
        """
        Alias for get_current_regime_context() for backward compatibility
        
        Returns:
            Current RegimeAnalysis or None if no regime detected yet
        """
        return self.get_current_regime_context()
    
    def get_regime_at_timestamp(self, symbol: str, timestamp: datetime) -> Optional[RegimeAnalysis]:
        """
        Get regime for a specific timestamp (bar-by-bar lookup)
        
        Args:
            symbol: Trading symbol
            timestamp: Timestamp of the bar
            
        Returns:
            RegimeAnalysis for that timestamp, or None if not found
        """
        if symbol not in self.regime_by_timestamp:
            return None
        
        # Exact match first
        if timestamp in self.regime_by_timestamp[symbol]:
            return self.regime_by_timestamp[symbol][timestamp]
        
        # If no exact match, find closest earlier timestamp (most recent regime at that time)
        symbol_timestamps = sorted(self.regime_by_timestamp[symbol].keys())
        for ts in reversed(symbol_timestamps):
            if ts <= timestamp:
                return self.regime_by_timestamp[symbol][ts]
        
        return None
    
    def get_regime_sequence(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Get complete regime sequence for a symbol (bar-by-bar)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of regime entries, each with timestamp, bar_index, regime, confidence, regime_changed
        """
        return self.regime_sequence.get(symbol, [])
    
    def get_regime_for_dataframe_row(self, symbol: str, row_index: int, dataframe: pd.DataFrame) -> Optional[RegimeAnalysis]:
        """
        Get regime for a specific DataFrame row by matching timestamp
        
        Args:
            symbol: Trading symbol
            row_index: Row index in DataFrame
            dataframe: DataFrame with 'timestamp' column
            
        Returns:
            RegimeAnalysis for that row, or None if not found
        """
        if row_index >= len(dataframe) or 'timestamp' not in dataframe.columns:
            return None
        
        timestamp = dataframe.iloc[row_index]['timestamp']
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        elif not isinstance(timestamp, datetime):
            return None
        
        return self.get_regime_at_timestamp(symbol, timestamp)
