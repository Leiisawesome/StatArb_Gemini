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
from collections import deque
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass
import uuid
import asyncio
import math

# Import ISystemComponent for orchestrator integration (Rule 1)
from ..system.interfaces import ISystemComponent, IRegimePolicy, IRegimeSubscriber
from core_engine.exceptions import ConfigurationRequiredError

# Import centralized configuration (Rule 1, Section 7)
from ..config.component_config import RegimeConfig

# Import canonical MarketRegime from type_definitions (Single Source of Truth)
from ..type_definitions.regime import MarketRegime, MarketRegimeState, TimeframeRegime, MLTransitionPrediction

# === BACKWARD COMPATIBILITY ALIASES ===
RegimeAnalysis = MarketRegimeState
RegimeTransitionPrediction = MLTransitionPrediction
RegimeType = MarketRegime

logger = logging.getLogger(__name__)

class RealTimeRegimeSensor(ISystemComponent, IRegimePolicy):
    """
    Real-Time Market Regime Sensor

    Institutional-grade low-latency market regime detection:
    - Market regime detection and classification (Real-time path)
    - Multi-timeframe EWMA-based analysis
    - Designed for intraday per-bar updates
    - Feeds data to RegimeManager (Strategic Brain)
    """

    def __init__(self, config: Dict[str, Any]):
        # Initialize with centralized RegimeConfig (Rule 1, Section 7)
        if config is None:
            from ..config.component_config import RegimeConfig
            self.config = RegimeConfig()
        elif isinstance(config, dict):
            from ..config.component_config import RegimeConfig
            self.config = RegimeConfig(**config)
        elif hasattr(config, '__dict__'):
            # Already a config object
            self.config = config
        else:
            raise ConfigurationRequiredError("Invalid config type for RealTimeRegimeSensor")

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("✅ Real-Time Regime Sensor initialized")

        # Sensor identification
        self.sensor_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.start_time: Optional[datetime] = None
        self.component_id: Optional[str] = None

        # Health metrics
        self.health_metrics = {
            'component_type': 'RealTimeRegimeSensor',
            'last_update': datetime.now(),
            'error_count': 0,
            'warning_count': 0,
            'regime_count': 0,
            'average_confidence': 0.0,
            'latency_ms': 0.0,
            'initialization_status': 'not_started',
            'performance_metrics': {
                'total_regime_analyses': 0,
                'successful_regime_analyses': 0,
                'failed_regime_analyses': 0,
                'average_analysis_time': 0.0,
                'regime_changes_detected': 0
            }
        }

        # Current regime state
        self.current_regime: Optional[MarketRegimeState] = None
        
        # CRITICAL: Bar-by-bar regime sequence persistence (for regime-aware processing)
        # Maps symbol -> deque[Dict] with regime for each bar (timestamp-indexed)
        # P0 Fix: Use bounded deques to prevent memory leak
        self.regime_sequence: Dict[str, deque] = {}
        # Maps symbol -> Dict[timestamp] -> regime for O(1) lookup (bounded by regime_sequence size)
        self.regime_by_timestamp: Dict[str, Dict[datetime, MarketRegimeState]] = {}

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

        # ------------------------------------------------------------------
        # Per-bar fast regime state (single-symbol incremental evaluator)
        # ------------------------------------------------------------------
        self._fast_state: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"🚀 Real-Time Regime Sensor initialized with ID: {self.sensor_id}")

    def _fast_regime_enabled(self) -> bool:
        return bool(getattr(self.config, "enable_per_bar_fast", False))

    def _evaluate_fast_single_symbol(self, market_data: pd.DataFrame, symbol: str) -> RegimeAnalysis:
        """
        O(1) per-bar single-symbol regime evaluator.

        - Maintains per-symbol EWMA volatility (fast/slow) and EWMA trend.
        - Classifies directional + volatility regime and emits a RegimeAnalysis.
        - Designed for intraday per-bar updates without expensive pandas rolling ops.
        """
        sym = (symbol or "").upper() or "UNKNOWN"
        if market_data is None or len(market_data) == 0:
            ts = datetime.now()
            return RegimeAnalysis(primary_regime=MarketRegime.UNKNOWN, confidence=0.0, regime_duration=0, timestamp=ts)

        # Use last bar only
        last = market_data.iloc[-1]
        ts_val = last.get("timestamp") if isinstance(last, dict) else last["timestamp"] if "timestamp" in market_data.columns else None
        ts = pd.to_datetime(ts_val, errors="coerce")
        if isinstance(ts, pd.Timestamp):
            ts = ts.to_pydatetime()
        if not isinstance(ts, datetime):
            ts = datetime.now()

        close_val = None
        try:
            close_val = float(last.get("close")) if isinstance(last, dict) else float(last["close"])
        except Exception:
            close_val = float(market_data["close"].iloc[-1]) if "close" in market_data.columns else None
        if close_val is None or not np.isfinite(close_val) or close_val <= 0:
            return RegimeAnalysis(primary_regime=MarketRegime.UNKNOWN, confidence=0.0, regime_duration=0, timestamp=ts)

        st = self._fast_state.get(sym)
        if st is None:
            st = {
                "last_close": close_val,
                "bars": 1,
                "ewma_var_fast": 0.0,
                "ewma_var_slow": 0.0,
                "ewma_trend": 0.0,
                "regime_duration": 0,
                "last_primary": MarketRegime.UNKNOWN,
            }
            self._fast_state[sym] = st
            return RegimeAnalysis(primary_regime=MarketRegime.UNKNOWN, confidence=0.0, regime_duration=0, timestamp=ts)

        last_close = float(st.get("last_close") or close_val)
        st["last_close"] = close_val
        st["bars"] = int(st.get("bars", 0) or 0) + 1

        # Log return
        r = 0.0
        if last_close > 0:
            r = math.log(close_val / last_close) if close_val > 0 else 0.0

        lam_f = float(getattr(self.config, "per_bar_fast_lambda_fast", 0.97))
        lam_s = float(getattr(self.config, "per_bar_fast_lambda_slow", 0.995))
        lam_t = float(getattr(self.config, "per_bar_fast_lambda_trend", 0.95))

        # EWMA variance update
        vf = float(st.get("ewma_var_fast", 0.0) or 0.0)
        vs = float(st.get("ewma_var_slow", 0.0) or 0.0)
        vf = lam_f * vf + (1.0 - lam_f) * (r * r)
        vs = lam_s * vs + (1.0 - lam_s) * (r * r)
        st["ewma_var_fast"] = vf
        st["ewma_var_slow"] = vs

        # EWMA trend update
        tr = float(st.get("ewma_trend", 0.0) or 0.0)
        tr = lam_t * tr + (1.0 - lam_t) * r
        st["ewma_trend"] = tr

        # Require minimum bars
        min_bars = int(getattr(self.config, "per_bar_min_bars", 30))
        if int(st["bars"]) < min_bars:
            return RegimeAnalysis(primary_regime=MarketRegime.UNKNOWN, confidence=0.0, regime_duration=0, timestamp=ts)

        vol_fast = math.sqrt(max(vf, 0.0))
        vol_slow = math.sqrt(max(vs, 0.0))
        vol_ratio = vol_fast / (vol_slow + 1e-12)

        # Absolute volatility (annualized) is needed for realistic "extreme_volatility" detection.
        # Using only vol_ratio fails when both fast/slow vols rise together (ratio ~ 1),
        # which is common in true high-volatility regimes.
        # Assumption: intraday minute bars (~390 bars/day, ~252 trading days/year).
        ann_factor = math.sqrt(390.0 * 252.0)
        ann_vol = float(vol_fast * ann_factor)

        # Direction
        trend_th = float(getattr(self.config, "per_bar_trend_threshold", 2e-4))
        if tr > trend_th:
            direction = "bull"
        elif tr < -trend_th:
            direction = "bear"
        else:
            direction = "sideways"

        # Vol regime (two signals):
        # - **Absolute vol** (primary) → maps to execution cost multipliers.
        # - **Fast/slow ratio** (secondary) → captures sudden vol regime changes.
        ann_low = float(getattr(self.config, "per_bar_vol_annual_low", 0.20))
        ann_high = float(getattr(self.config, "per_bar_vol_annual_high", 0.40))
        ann_extreme = float(getattr(self.config, "per_bar_vol_annual_extreme", 0.60))
        ann_crisis = float(getattr(self.config, "per_bar_vol_annual_crisis", 0.90))

        if ann_vol >= ann_crisis:
            vol_reg_label = "crisis"
        elif ann_vol >= ann_extreme:
            vol_reg_label = "extreme_volatility"
        elif ann_vol >= ann_high:
            vol_reg_label = "high_volatility"
        elif ann_vol <= ann_low:
            vol_reg_label = "low_volatility"
        else:
            vol_reg_label = "normal_volatility"

        # Secondary: detect sudden vol *changes* using ratio thresholds.
        vr_high = float(getattr(self.config, "per_bar_vol_ratio_high", 1.5))
        vr_low = float(getattr(self.config, "per_bar_vol_ratio_low", 0.7))
        if vol_ratio >= vr_high and vol_reg_label in ("low_volatility", "normal_volatility"):
            vol_reg_label = "high_volatility"
        elif vol_ratio <= vr_low and vol_reg_label in ("high_volatility", "extreme_volatility", "crisis"):
            vol_reg_label = "normal_volatility"

        # For primary regime classification helper, collapse into {low, normal, high}.
        # (We keep the richer label in RegimeAnalysis.volatility_regime for execution costs.)
        if vol_reg_label in ("crisis", "extreme_volatility", "high_volatility"):
            vol_reg = "high"
        elif vol_reg_label == "low_volatility":
            vol_reg = "low"
        else:
            vol_reg = "normal"

        primary = MarketRegime.from_direction_and_vol(direction if direction in ("bull", "bear") else "neutral", vol_reg)
        # Map "neutral" direction to range-like regimes
        if direction == "sideways":
            primary = MarketRegime.RANGE_BOUND if vol_reg != "high" else MarketRegime.CHOPPY

        # Trend strength: normalize by volatility (proxy)
        trend_strength = float(min(1.0, abs(tr) / (vol_fast + 1e-12) / 5.0))  # heuristic scaling

        # Confidence: higher when vol signals are stable and trend strength is clear
        conf = float(min(1.0, 0.5 + 0.5 * max(trend_strength, min(1.0, abs(vol_ratio - 1.0)))))

        # Duration tracking
        last_primary = st.get("last_primary", MarketRegime.UNKNOWN)
        if primary == last_primary:
            st["regime_duration"] = int(st.get("regime_duration", 0) or 0) + 1
        else:
            st["regime_duration"] = 1
            st["last_primary"] = primary

        ra = RegimeAnalysis(
            primary_regime=primary,
            confidence=conf,
            regime_duration=int(st["regime_duration"]),
            timestamp=ts,
            directional_regime=direction if direction != "sideways" else "neutral",
            volatility_regime=vol_reg_label,
            trend_strength=trend_strength,
            transition_probability=float(min(1.0, abs(vol_ratio - 1.0))),
        )
        return ra

    @property
    def regime_history(self) -> List[RegimeAnalysis]:
        """Return regime history as list for backward compatibility."""
        return list(self._regime_history)

    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================

    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel

        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="RealTimeRegimeSensor",
            component=self,
            layer=ComponentLayer.SUPPORT,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=5  # Layer 0: REGIME-FIRST - Foundation for all components
        )

        self.logger.info(f"✅ RealTimeRegimeSensor registered with orchestrator: {self.component_id}")
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
        """Initialize the Real-Time Regime Sensor"""
        try:
            self.logger.info("🔄 Initializing Real-Time Regime Sensor...")

            # Initialize regime analysis engines
            await self._initialize_regime_engines()

            # Initialize monitoring
            await self._initialize_monitoring_system()

            # Update status
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'

            self.logger.info("✅ Real-Time Regime Sensor initialization complete")
            return True

        except Exception as e:
            self.logger.error(f"❌ Real-Time Regime Sensor initialization failed: {e}")
            self.health_metrics['error_count'] += 1
            self.health_metrics['initialization_status'] = 'failed'
            return False

    async def start(self) -> bool:
        """Start the Real-Time Regime Sensor"""
        if not self.is_initialized:
            self.logger.error("Cannot start Real-Time Regime Sensor: not initialized")
            return False

        try:
            self.logger.info("🚀 Starting Real-Time Regime Sensor...")

            # Start regime analysis
            await self._start_regime_analysis()

            # Start monitoring
            await self._start_monitoring()

            # Update status
            self.is_operational = True
            self.start_time = datetime.now()
            self.health_metrics['operational_status'] = 'active'

            self.logger.info("✅ Real-Time Regime Sensor started successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Real-Time Regime Sensor start failed: {e}")
            self.health_metrics['error_count'] += 1
            return False

    async def stop(self) -> bool:
        """Stop the Real-Time Regime Sensor"""
        try:
            self.logger.info("🛑 Stopping Real-Time Regime Sensor...")

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

            self.logger.info("✅ Real-Time Regime Sensor stopped successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Real-Time Regime Sensor stop failed: {e}")
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

    async def shutdown(self) -> None:
        """Shutdown the component (ISystemComponent interface)"""
        self.logger.info("🛑 Shutting down Real-Time Regime Sensor...")
        self.is_operational = False
        self.is_initialized = False
        self.health_metrics['last_update'] = datetime.now()

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
                    self._regime_history.append(new_regime)

                    # Note: deque(maxlen=1000) auto-removes oldest entries

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
                            # This can fire frequently in intraday mode; keep at DEBUG to avoid log spam.
                            self.logger.debug(
                                f"Regime change detected for {symbol} at {timestamp}: "
                                f"{self.current_regime.primary_regime.value} -> {new_regime.primary_regime.value}"
                            )

                        # Update current regime (this is the regime at THIS bar)
                        self.current_regime = new_regime
                        self._regime_history.append(new_regime)

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
                        # P0 Fix: Use bounded deque(maxlen=10000) per symbol
                        if symbol not in self.regime_sequence:
                            self.regime_sequence[symbol] = deque(maxlen=10000)
                        self.regime_sequence[symbol].append(regime_entry)

                        # CRITICAL: Persist regime by timestamp for O(1) lookup
                        if symbol not in self.regime_by_timestamp:
                            self.regime_by_timestamp[symbol] = {}
                        self.regime_by_timestamp[symbol][timestamp] = new_regime

                        # Note: regime_sequence uses deque(maxlen=10000) for auto-eviction
                        # Clean up timestamp index periodically to prevent memory buildup
                        # Only clean when timestamp dict grows significantly larger than sequence
                        if len(self.regime_by_timestamp[symbol]) > len(self.regime_sequence[symbol]) * 1.5:
                            # Get valid timestamps from current sequence
                            valid_timestamps = {entry.get('timestamp') for entry in self.regime_sequence[symbol]}
                            # Remove stale timestamp entries
                            stale_keys = [k for k in self.regime_by_timestamp[symbol] if k not in valid_timestamps]
                            for k in stale_keys:
                                del self.regime_by_timestamp[symbol][k]

                        # Note: _regime_history uses deque(maxlen=1000) for auto-eviction

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
        momentum = indicators['momentum']  # Used for future enhancements
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
        elif directional == "sideways":
            # Handle sideways/consolidation regimes based on volatility
            if vol_regime in ["high_volatility", "extreme_volatility"]:
                # Sideways with high volatility = choppy market
                primary_regime = MarketRegime.CHOPPY
                confidence = 0.65
            else:
                # Sideways with low/normal volatility = range-bound
                primary_regime = MarketRegime.RANGE_BOUND
                confidence = 0.75
        elif vol_regime == "extreme_volatility":
            # Extreme volatility regardless of direction = choppy
            primary_regime = MarketRegime.CHOPPY
            confidence = 0.65
        else:
            # Fallback to range-bound for any unhandled case (defensive coding)
            primary_regime = MarketRegime.RANGE_BOUND
            confidence = 0.6
            self.logger.warning(
                f"Unhandled regime combination: directional={directional}, vol_regime={vol_regime}. "
                f"Defaulting to RANGE_BOUND."
            )

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
        # If data is provided, process it
        if data is not None:
            return self.process_market_data(data)
            
        return {
            'regime_analysis_performed': True,
            'input_data_type': type(data).__name__,
            'processing_timestamp': datetime.now(),
            'processing_component': 'RealTimeRegimeSensor'
        }

    def detect_regime(self, data: Any, **kwargs) -> Optional[MarketRegimeState]:
        """Standardized method for regime detection (IRegimePolicy interface)"""
        # Process data if provided
        if data is not None:
            self.analyze_regime(data)
            
        return self.current_regime

    def get_capabilities(self) -> Dict[str, Any]:
        """Returns metadata about what this policy can detect (IRegimePolicy interface)"""
        return {
            "policy_type": "Tactical",
            "latency_profile": "Low (Real-Time)",
            "update_mode": "Incremental/Bar-by-Bar",
            "capabilities": [
                "multi_timeframe_analysis",
                "volatility_regime_detection",
                "trend_alignment",
                "ml_transition_prediction"
            ],
            "input_formats": ["Dict[BarData]", "pd.DataFrame (Single Symbol)"]
        }

    def classify_regime(self, data: Any) -> Optional[MarketRegimeState]:
        """Standardized method for regime classification (alias)"""
        return self.detect_regime(data)

    # ========================================
    # REGIME ACCESS METHODS (for component integration)
    # ========================================

    def get_current_regime_context(self) -> Optional[MarketRegimeState]:
        """
        Get current regime context for components (IRegimeAware interface support)

        Returns:
            Current MarketRegimeState or None if no regime detected yet
        """
        return self.current_regime

    def get_current_regime(self) -> Optional[MarketRegimeState]:
        """
        Alias for get_current_regime_context() for backward compatibility

        Returns:
            Current MarketRegimeState or None if no regime detected yet
        """
        return self.get_current_regime_context()

    def get_regime_at_timestamp(self, symbol: str, timestamp: datetime) -> Optional[MarketRegimeState]:
        """
        Get regime for a specific timestamp (bar-by-bar lookup)

        Args:
            symbol: Trading symbol
            timestamp: Timestamp of the bar

        Returns:
            MarketRegimeState for that timestamp, or None if not found
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
        # Convert deque to list for backward compatibility
        seq = self.regime_sequence.get(symbol)
        return list(seq) if seq else []

    def get_regime_for_dataframe_row(self, symbol: str, row_index: int, dataframe: pd.DataFrame) -> Optional[MarketRegimeState]:
        """
        Get regime for a specific DataFrame row by matching timestamp

        Args:
            symbol: Trading symbol
            row_index: Row index in DataFrame
            dataframe: DataFrame with 'timestamp' column

        Returns:
            MarketRegimeState for that row, or None if not found
        """
        if row_index >= len(dataframe) or 'timestamp' not in dataframe.columns:
            return None

        timestamp = dataframe.iloc[row_index]['timestamp']
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        elif not isinstance(timestamp, datetime):
            return None

        return self.get_regime_at_timestamp(symbol, timestamp)

    # ========================================
    # CAUSAL-ONLY MODE (Paper Trading Evolution)
    # ========================================

    def enable_causal_only_mode(self) -> None:
        """
        Enable causal-only mode for paper trading.

        In this mode:
        - Only filtered (causal) probabilities are used
        - No future-looking smoothed probabilities
        - Regime changes require 2-step confirmation
        """
        self._causal_only_mode = True
        self._confirmation_state = 'CONFIRMED'  # Start with confirmed current regime
        self._pending_regime: Optional[MarketRegimeState] = None
        self._pending_count = 0
        self._confirmation_required = 2  # Consecutive agreeing evaluations
        self.logger.info("✅ Causal-only mode enabled for paper trading")

    def disable_causal_only_mode(self) -> None:
        """Disable causal-only mode (for backtest with full data)."""
        self._causal_only_mode = False
        self._confirmation_state = None
        self._pending_regime = None
        self.logger.info("Causal-only mode disabled")

    def is_causal_only_mode(self) -> bool:
        """Check if causal-only mode is enabled."""
        return getattr(self, '_causal_only_mode', False)

    def evaluate_regime_causal(
        self,
        market_data: pd.DataFrame,
        symbol: Optional[str] = None,
    ) -> MarketRegimeState:
        """
        Evaluate regime using causal-only data (no look-ahead).

        Args:
            market_data: DataFrame with OHLCV data up to current bar
            symbol: Optional symbol for regime tracking

        Returns:
            Confirmed regime (may be lagged during confirmation)
        """
        # Get raw regime detection
        if symbol and self._fast_regime_enabled():
            raw_regime = self._evaluate_fast_single_symbol(market_data, symbol)
        else:
            # Fallback to standard process_market_data if needed
            res = self.process_market_data(market_data)
            raw_regime = self.current_regime

        if not self.is_causal_only_mode():
            return raw_regime

        # Apply confirmation state machine
        confirmed_regime = self._apply_confirmation_state_machine(raw_regime)
        return confirmed_regime

    def _apply_confirmation_state_machine(self, new_regime: MarketRegimeState) -> MarketRegimeState:
        """Apply 2-step confirmation state machine for regime changes."""
        current_confirmed = self.current_regime
        if current_confirmed is None:
            self._confirmation_state = 'CONFIRMED'
            return new_regime

        current_primary = current_confirmed.primary_regime
        new_primary = new_regime.primary_regime

        if self._confirmation_state == 'CONFIRMED':
            if new_primary == current_primary:
                return new_regime
            else:
                self._confirmation_state = 'PENDING'
                self._pending_regime = new_regime
                self._pending_count = 1
                return current_confirmed
        elif self._confirmation_state == 'PENDING':
            pending_primary = self._pending_regime.primary_regime if self._pending_regime else None
            if new_primary == pending_primary:
                self._pending_count += 1
                if self._pending_count >= 2:
                    self._confirmation_state = 'CONFIRMED'
                    self._pending_regime = None
                    self._pending_count = 0
                    return new_regime
                return current_confirmed
            else:
                self._confirmation_state = 'CONFIRMED'
                self._pending_regime = None
                self._pending_count = 0
                return current_confirmed
        return current_confirmed

    def process_market_data(self, market_data: Any) -> Dict[str, Any]:
        """
        Process market data for regime analysis (Simplified for Sensor)

        Args:
            market_data: Bar data or DataFrame

        Returns:
            Dict with processing results
        """
        try:
            if isinstance(market_data, pd.DataFrame):
                # Bar-by-bar processing
                symbol = market_data['symbol'].iloc[0] if 'symbol' in market_data.columns else 'UNKNOWN'
                last_regime = None
                
                for idx, row in market_data.iterrows():
                    regime_state = self._evaluate_fast_single_symbol(pd.DataFrame([row]), symbol)
                    
                    regime_changed = False
                    if self.current_regime and regime_state.primary_regime != self.current_regime.primary_regime:
                        regime_changed = True
                    
                    self.current_regime = regime_state
                    self._regime_history.append(regime_state)
                    
                    # Persist
                    if symbol not in self.regime_by_timestamp:
                        self.regime_by_timestamp[symbol] = {}
                    self.regime_by_timestamp[symbol][row.get('timestamp', datetime.now())] = regime_state
                    
                    last_regime = regime_state

                return {
                    'market_data_processed': True,
                    'symbol': symbol,
                    'regime_detected': last_regime.primary_regime.value if last_regime else None,
                    'processing_timestamp': datetime.now()
                }
            return {'market_data_processed': False, 'error': 'Unsupported data format'}
        except Exception as e:
            self.logger.error(f"Error in sensor process_market_data: {e}")
            return {'market_data_processed': False, 'error': str(e)}

# === Backward Compatibility Alias ===
EnhancedRegimeEngine = RealTimeRegimeSensor
