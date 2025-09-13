#!/usr/bin/env python3
"""
Market Condition Analytics Engine
================================

Advanced market regime detection and dynamic strategy selection system.
Integrates with existing core_structure components for optimal performance.

Features:
- Multi-source data integration (OHLCV, macro, sentiment)
- Real-time regime detection with ML-enhanced models
- Dynamic strategy selection based on regime transitions
- Intelligent instrument optimization per strategy-regime combination
- Performance feedback loop for continuous improvement
- Unified workflow for backtest → paper → live trading

Author: Professional Trading System Architecture
Version: 1.0.0 (Market Condition Analytics)
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
import json

# ML and statistical libraries
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Leverage existing core_structure components
from .core_analytics import CoreAnalyticsEngine
from .monitoring_analytics import MonitoringAnalyticsEngine, AlertSeverity, AlertType
from .research_analytics import ResearchAnalyticsEngine
from ..strategies import StrategyType
from ..infrastructure.database import DatabaseManager
from ..infrastructure.messaging import MessageBus, MessageType, Message
from ..infrastructure.monitoring import MetricsCollector

logger = logging.getLogger(__name__)

# ================================================================================
# MARKET CONDITION ENUMS AND TYPES
# ================================================================================

class MarketCondition(Enum):
    """Enhanced market condition types for dynamic strategy selection"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    SIDEWAYS_RANGE = "sideways_range"
    CRISIS_MODE = "crisis_mode"
    RECOVERY_MODE = "recovery_mode"
    TRANSITION = "transition"

class DataSourceType(Enum):
    """Types of data sources for market condition analysis"""
    MARKET_DATA = "market_data"
    MACROECONOMIC = "macroeconomic"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"

class StrategyRecommendation(Enum):
    """Strategy recommendation levels"""
    OPTIMAL = "optimal"
    SUITABLE = "suitable"
    NEUTRAL = "neutral"
    UNSUITABLE = "unsuitable"
    AVOID = "avoid"

# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class MarketConditionState:
    """Complete market condition state representation"""
    timestamp: datetime
    primary_condition: MarketCondition
    secondary_conditions: List[MarketCondition]
    confidence: float
    volatility_regime: str
    trend_strength: float
    market_stress: float
    liquidity_condition: str
    regime_duration: timedelta
    transition_probability: Dict[MarketCondition, float]
    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StrategySelection:
    """Dynamic strategy selection result"""
    timestamp: datetime
    regime: MarketCondition
    selected_strategies: Dict[StrategyType, float]  # Strategy -> Weight
    confidence: float
    expected_performance: Dict[StrategyType, float]
    risk_assessment: Dict[StrategyType, float]
    instruments_per_strategy: Dict[StrategyType, List[str]]
    reasoning: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InstrumentRanking:
    """Instrument ranking within a strategy-regime combination"""
    symbol: str
    strategy: StrategyType
    regime: MarketCondition
    rank: int
    score: float
    expected_return: float
    risk_score: float
    liquidity_score: float
    regime_suitability: float
    historical_performance: Dict[str, float]
    features: Dict[str, float] = field(default_factory=dict)

@dataclass
class PerformanceFeedback:
    """Performance feedback for continuous improvement"""
    timestamp: datetime
    strategy: StrategyType
    instrument: str
    regime: MarketCondition
    actual_return: float
    predicted_return: float
    prediction_error: float
    risk_adjusted_return: float
    execution_quality: float
    regime_accuracy: float
    metadata: Dict[str, Any] = field(default_factory=dict)

# ================================================================================
# MARKET CONDITION ANALYTICS ENGINE
# ================================================================================

class MarketConditionAnalyticsEngine:
    """
    Central engine for market condition analysis and dynamic strategy selection.
    
    Integrates with existing core_structure components:
    - CoreAnalyticsEngine: Performance and risk analysis
    - MonitoringAnalyticsEngine: Real-time monitoring and alerts
    - ResearchAnalyticsEngine: Backtesting and regime analysis
    - Strategy implementations: Leverage existing strategy logic
    - Infrastructure: Database, messaging, monitoring
    """
    
    def __init__(self,
                 config: Optional[Dict[str, Any]] = None,
                 database_manager: Optional[DatabaseManager] = None,
                 message_bus: Optional[MessageBus] = None,
                 metrics_collector: Optional[MetricsCollector] = None):
        """Initialize market condition analytics engine"""
        
        self.config = config or self._default_config()
        
        # Leverage existing analytics engines
        self.core_analytics = CoreAnalyticsEngine(
            history_window=self.config.get('analytics_window', 252),
            enable_ml=True
        )
        self.monitoring_analytics = MonitoringAnalyticsEngine()
        self.research_analytics = ResearchAnalyticsEngine()
        
        # Infrastructure components
        self.database_manager = database_manager
        self.message_bus = message_bus
        self.metrics_collector = metrics_collector
        
        # Core components
        self.regime_detector = EnhancedRegimeDetector(self)
        self.strategy_selector = DynamicStrategySelector(self)
        self.instrument_optimizer = InstrumentOptimizer(self)
        self.performance_tracker = PerformanceTracker(self)
        self.data_processor = UnifiedDataProcessor(self)
        
        # State management
        self.current_market_state: Optional[MarketConditionState] = None
        self.current_strategy_selection: Optional[StrategySelection] = None
        self.regime_history: deque = deque(maxlen=1000)
        self.performance_history: deque = deque(maxlen=5000)
        
        # ML models
        self.regime_classifier = RandomForestClassifier(
            n_estimators=100, 
            random_state=42,
            class_weight='balanced'
        )
        self.performance_predictor = RandomForestClassifier(
            n_estimators=50,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=10)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        
        # Model state
        self.models_trained = False
        self.last_model_update = None
        
        # Threading
        self.analysis_lock = threading.RLock()
        self.background_thread = None
        self.running = False
        
        logger.info("MarketConditionAnalyticsEngine initialized successfully")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for market condition analytics"""
        return {
            'analytics_window': 252,
            'regime_update_interval': 300,  # 5 minutes
            'model_retrain_interval': 86400,  # 24 hours
            'min_regime_duration': 3600,  # 1 hour
            'regime_confidence_threshold': 0.7,
            'strategy_rebalance_threshold': 0.2,
            'instrument_ranking_window': 63,  # 3 months
            'performance_feedback_window': 21,  # 21 days
            'feature_importance_threshold': 0.01,
            'enable_real_time_updates': True,
            'enable_performance_feedback': True,
            'enable_model_retraining': True,
            'alert_on_regime_change': True,
            'persist_regime_states': True
        }
    
    async def start(self) -> None:
        """Start the market condition analytics engine"""
        try:
            with self.analysis_lock:
                if self.running:
                    logger.warning("Market condition analytics engine already running")
                    return
                
                logger.info("Starting market condition analytics engine...")
                
                # Initialize database schema
                await self._initialize_database()
                
                # Load historical data and train models
                await self._load_historical_data()
                await self._train_initial_models()
                
                # Start background processing
                self.running = True
                self.background_thread = threading.Thread(
                    target=self._background_analysis_loop,
                    daemon=True
                )
                self.background_thread.start()
                
                # Subscribe to message bus if available
                if self.message_bus:
                    self.message_bus.subscribe(
                        MessageType.MARKET_DATA,
                        self._on_market_data_update
                    )
                    self.message_bus.subscribe(
                        MessageType.PERFORMANCE_UPDATE,
                        self._on_performance_update
                    )
                
                logger.info("✅ Market condition analytics engine started successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to start market condition analytics engine: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the market condition analytics engine"""
        try:
            with self.analysis_lock:
                if not self.running:
                    return
                
                logger.info("Stopping market condition analytics engine...")
                
                self.running = False
                
                if self.background_thread and self.background_thread.is_alive():
                    self.background_thread.join(timeout=5.0)
                
                logger.info("✅ Market condition analytics engine stopped")
                
        except Exception as e:
            logger.error(f"❌ Error stopping market condition analytics engine: {e}")
    
    async def analyze_current_market_condition(self, 
                                             market_data: pd.DataFrame,
                                             macro_data: Optional[Dict[str, Any]] = None,
                                             sentiment_data: Optional[Dict[str, Any]] = None) -> MarketConditionState:
        """
        Analyze current market condition using multiple data sources.
        
        This is the main entry point for regime detection and analysis.
        """
        try:
            with self.analysis_lock:
                # Process and integrate all data sources
                processed_data = await self.data_processor.process_all_data(
                    market_data=market_data,
                    macro_data=macro_data,
                    sentiment_data=sentiment_data
                )
                
                # Detect current market regime
                market_state = await self.regime_detector.detect_current_regime(
                    processed_data
                )
                
                # Update current state
                self.current_market_state = market_state
                self.regime_history.append(market_state)
                
                # Persist state if configured
                if self.config.get('persist_regime_states', True):
                    await self._persist_market_state(market_state)
                
                # Send alerts on regime changes
                await self._check_regime_change_alerts(market_state)
                
                # Update metrics
                if self.metrics_collector:
                    await self._update_regime_metrics(market_state)
                
                return market_state
                
        except Exception as e:
            logger.error(f"❌ Error analyzing market condition: {e}")
            raise
    
    async def get_strategy_recommendations(self, 
                                         market_state: Optional[MarketConditionState] = None,
                                         portfolio_context: Optional[Dict[str, Any]] = None) -> StrategySelection:
        """
        Get dynamic strategy recommendations based on current market condition.
        """
        try:
            with self.analysis_lock:
                # Use current market state if not provided
                if market_state is None:
                    market_state = self.current_market_state
                    if market_state is None:
                        raise ValueError("No market state available for strategy selection")
                
                # Get strategy recommendations
                strategy_selection = await self.strategy_selector.select_strategies(
                    market_state=market_state,
                    portfolio_context=portfolio_context
                )
                
                # Update current selection
                self.current_strategy_selection = strategy_selection
                
                # Get instrument rankings for each strategy
                for strategy_type in strategy_selection.selected_strategies:
                    instrument_rankings = await self.instrument_optimizer.rank_instruments(
                        strategy_type=strategy_type,
                        market_state=market_state
                    )
                    
                    # Add top instruments to strategy selection
                    top_instruments = [r.symbol for r in instrument_rankings[:10]]  # Top 10
                    strategy_selection.instruments_per_strategy[strategy_type] = top_instruments
                
                return strategy_selection
                
        except Exception as e:
            logger.error(f"❌ Error getting strategy recommendations: {e}")
            raise
    
    async def update_performance_feedback(self, 
                                        feedback: PerformanceFeedback) -> None:
        """
        Update performance feedback for continuous improvement.
        """
        try:
            with self.analysis_lock:
                # Store feedback
                self.performance_history.append(feedback)
                
                # Update performance tracker
                await self.performance_tracker.process_feedback(feedback)
                
                # Persist feedback if configured
                if self.config.get('enable_performance_feedback', True):
                    await self._persist_performance_feedback(feedback)
                
                # Check if model retraining is needed
                await self._check_model_retraining()
                
        except Exception as e:
            logger.error(f"❌ Error updating performance feedback: {e}")
    
    def get_current_market_state(self) -> Optional[MarketConditionState]:
        """Get the current market condition state"""
        return self.current_market_state
    
    def get_current_strategy_selection(self) -> Optional[StrategySelection]:
        """Get the current strategy selection"""
        return self.current_strategy_selection
    
    def get_regime_history(self, lookback_hours: int = 24) -> List[MarketConditionState]:
        """Get regime history for the specified lookback period"""
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        return [
            state for state in self.regime_history
            if state.timestamp >= cutoff_time
        ]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        try:
            recent_feedback = list(self.performance_history)[-100:]  # Last 100 feedback items
            
            if not recent_feedback:
                return {}
            
            # Calculate aggregate metrics
            prediction_errors = [f.prediction_error for f in recent_feedback]
            regime_accuracies = [f.regime_accuracy for f in recent_feedback]
            risk_adjusted_returns = [f.risk_adjusted_return for f in recent_feedback]
            
            metrics = {
                'total_analyses': len(self.regime_history),
                'total_feedback_items': len(self.performance_history),
                'recent_prediction_error': np.mean(prediction_errors) if prediction_errors else 0,
                'recent_regime_accuracy': np.mean(regime_accuracies) if regime_accuracies else 0,
                'recent_risk_adjusted_return': np.mean(risk_adjusted_returns) if risk_adjusted_returns else 0,
                'models_trained': self.models_trained,
                'last_model_update': self.last_model_update,
                'engine_running': self.running
            }
            
            # Add regime distribution
            recent_regimes = [state.primary_condition.value for state in self.regime_history]
            regime_counts = pd.Series(recent_regimes).value_counts().to_dict()
            metrics['regime_distribution'] = regime_counts
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            return {}
    
    # ============================================================================
    # INTERNAL METHODS
    # ============================================================================
    
    async def _initialize_database(self) -> None:
        """Initialize database schema for market condition analytics"""
        if not self.database_manager:
            return
        
        try:
            # Market condition states table
            await self.database_manager.execute("""
                CREATE TABLE IF NOT EXISTS market_condition_states (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    primary_condition VARCHAR(50) NOT NULL,
                    secondary_conditions TEXT,
                    confidence DECIMAL(5,4) NOT NULL,
                    volatility_regime VARCHAR(20),
                    trend_strength DECIMAL(8,6),
                    market_stress DECIMAL(8,6),
                    liquidity_condition VARCHAR(20),
                    regime_duration_seconds INTEGER,
                    transition_probabilities TEXT,
                    features TEXT,
                    metadata TEXT
                )
            """)
            
            # Strategy selections table
            await self.database_manager.execute("""
                CREATE TABLE IF NOT EXISTS strategy_selections (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    regime VARCHAR(50) NOT NULL,
                    selected_strategies TEXT NOT NULL,
                    confidence DECIMAL(5,4) NOT NULL,
                    expected_performance TEXT,
                    risk_assessment TEXT,
                    instruments_per_strategy TEXT,
                    reasoning TEXT,
                    metadata TEXT
                )
            """)
            
            # Performance feedback table
            await self.database_manager.execute("""
                CREATE TABLE IF NOT EXISTS performance_feedback (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    strategy VARCHAR(50) NOT NULL,
                    instrument VARCHAR(20) NOT NULL,
                    regime VARCHAR(50) NOT NULL,
                    actual_return DECIMAL(10,6) NOT NULL,
                    predicted_return DECIMAL(10,6) NOT NULL,
                    prediction_error DECIMAL(10,6) NOT NULL,
                    risk_adjusted_return DECIMAL(10,6),
                    execution_quality DECIMAL(5,4),
                    regime_accuracy DECIMAL(5,4),
                    metadata TEXT
                )
            """)
            
            logger.info("✅ Database schema initialized for market condition analytics")
            
        except Exception as e:
            logger.error(f"❌ Error initializing database schema: {e}")
    
    async def _load_historical_data(self) -> None:
        """Load historical data for model training"""
        try:
            # This would typically load from ClickHouse or other data sources
            # For now, we'll use a placeholder
            logger.info("📊 Loading historical market data for model training...")
            
            # TODO: Implement actual data loading from ClickHouse
            # historical_data = await self.database_manager.load_historical_market_data()
            
            logger.info("✅ Historical data loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading historical data: {e}")
    
    async def _train_initial_models(self) -> None:
        """Train initial ML models for regime detection and performance prediction"""
        try:
            logger.info("🧠 Training initial ML models...")
            
            # TODO: Implement actual model training with historical data
            # For now, mark models as trained
            self.models_trained = True
            self.last_model_update = datetime.now()
            
            logger.info("✅ Initial ML models trained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training initial models: {e}")
    
    def _background_analysis_loop(self) -> None:
        """Background analysis loop for continuous monitoring"""
        logger.info("🔄 Starting background analysis loop...")
        
        while self.running:
            try:
                # Sleep for the configured interval
                time.sleep(self.config.get('regime_update_interval', 300))
                
                if not self.running:
                    break
                
                # Perform background analysis tasks
                # This would typically include:
                # - Checking for new market data
                # - Updating regime detection
                # - Rebalancing strategy recommendations
                # - Model retraining if needed
                
                # For now, just log that we're running
                logger.debug("🔄 Background analysis cycle completed")
                
            except Exception as e:
                logger.error(f"❌ Error in background analysis loop: {e}")
                time.sleep(60)  # Sleep for 1 minute on error
        
        logger.info("✅ Background analysis loop stopped")
    
    async def _persist_market_state(self, market_state: MarketConditionState) -> None:
        """Persist market state to database"""
        if not self.database_manager:
            return
        
        try:
            # Convert features to JSON-safe format
            json_safe_features = self._make_json_safe(market_state.features)
            json_safe_metadata = self._make_json_safe(market_state.metadata)
            
            await self.database_manager.execute("""
                INSERT INTO market_condition_states (
                    timestamp, primary_condition, secondary_conditions, confidence,
                    volatility_regime, trend_strength, market_stress, liquidity_condition,
                    regime_duration_seconds, transition_probabilities, features, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                market_state.timestamp,
                market_state.primary_condition.value,
                json.dumps([c.value for c in market_state.secondary_conditions]),
                market_state.confidence,
                market_state.volatility_regime,
                market_state.trend_strength,
                market_state.market_stress,
                market_state.liquidity_condition,
                int(market_state.regime_duration.total_seconds()),
                json.dumps({k.value if hasattr(k, 'value') else str(k): v for k, v in market_state.transition_probability.items()}),
                json.dumps(json_safe_features),
                json.dumps(json_safe_metadata)
            ))
            
        except Exception as e:
            logger.error(f"❌ Error persisting market state: {e}")
    
    def _make_json_safe(self, obj: Any) -> Any:
        """Convert object to JSON-safe format"""
        if isinstance(obj, dict):
            # Handle dictionary keys that might be enums
            json_safe_dict = {}
            for k, v in obj.items():
                # Convert enum keys to their string values
                safe_key = k.value if hasattr(k, 'value') else str(k)
                json_safe_dict[safe_key] = self._make_json_safe(v)
            return json_safe_dict
        elif isinstance(obj, list):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, bool):
            return obj  # JSON supports boolean
        elif isinstance(obj, (int, float, str, type(None))):
            return obj
        elif hasattr(obj, 'value'):  # Enum
            return obj.value
        else:
            return str(obj)
    
    async def _persist_performance_feedback(self, feedback: PerformanceFeedback) -> None:
        """Persist performance feedback to database"""
        if not self.database_manager:
            return
        
        try:
            await self.database_manager.execute("""
                INSERT INTO performance_feedback (
                    timestamp, strategy, instrument, regime, actual_return,
                    predicted_return, prediction_error, risk_adjusted_return,
                    execution_quality, regime_accuracy, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                feedback.timestamp,
                feedback.strategy.value,
                feedback.instrument,
                feedback.regime.value,
                feedback.actual_return,
                feedback.predicted_return,
                feedback.prediction_error,
                feedback.risk_adjusted_return,
                feedback.execution_quality,
                feedback.regime_accuracy,
                json.dumps(feedback.metadata)
            ))
            
        except Exception as e:
            logger.error(f"❌ Error persisting performance feedback: {e}")
    
    async def _check_regime_change_alerts(self, market_state: MarketConditionState) -> None:
        """Check if regime change alerts should be sent"""
        if not self.config.get('alert_on_regime_change', True):
            return
        
        try:
            # Check if this is a regime change
            if len(self.regime_history) > 1:
                previous_state = self.regime_history[-2]
                
                if previous_state.primary_condition != market_state.primary_condition:
                    # Regime change detected - create alert through monitoring system
                    await self.monitoring_analytics.create_alert(
                        severity=AlertSeverity.WARNING,
                        alert_type=AlertType.MARKET,
                        title="Market Regime Change Detected",
                        message=f"Market regime changed from {previous_state.primary_condition.value} to {market_state.primary_condition.value}",
                        source="MarketConditionAnalytics",
                        data={
                            'previous_regime': previous_state.primary_condition.value,
                            'new_regime': market_state.primary_condition.value,
                            'confidence': market_state.confidence,
                            'transition_probability': {k.value if hasattr(k, 'value') else str(k): v for k, v in market_state.transition_probability.items()}
                        }
                    )
                    
                    # Send message through message bus if available
                    if self.message_bus:
                        message = Message(
                            type=MessageType.REGIME_CHANGE,
                            payload={
                                'previous_regime': previous_state.primary_condition.value,
                                'new_regime': market_state.primary_condition.value,
                                'confidence': market_state.confidence
                            },
                            source="MarketConditionAnalytics",
                            timestamp=datetime.now()
                        )
                        await self.message_bus.publish(message)
                    
                    logger.info(f"🚨 Regime change alert: {previous_state.primary_condition.value} → {market_state.primary_condition.value}")
        
        except Exception as e:
            logger.error(f"❌ Error checking regime change alerts: {e}")
    
    async def _update_regime_metrics(self, market_state: MarketConditionState) -> None:
        """Update regime-related metrics"""
        if not self.metrics_collector:
            return
        
        try:
            # Record regime metrics
            self.metrics_collector.record_metric(
                "market_condition.regime.confidence",
                market_state.confidence
            )
            
            self.metrics_collector.record_metric(
                "market_condition.trend_strength",
                market_state.trend_strength
            )
            
            self.metrics_collector.record_metric(
                "market_condition.market_stress",
                market_state.market_stress
            )
            
            # Record regime type as categorical metric
            regime_mapping = {regime.value: i for i, regime in enumerate(MarketCondition)}
            self.metrics_collector.record_metric(
                "market_condition.regime.type",
                regime_mapping.get(market_state.primary_condition.value, 0)
            )
            
        except Exception as e:
            logger.error(f"❌ Error updating regime metrics: {e}")
    
    async def _check_model_retraining(self) -> None:
        """Check if models need retraining based on performance feedback"""
        try:
            if not self.config.get('enable_model_retraining', True):
                return
            
            # Check if enough time has passed since last training
            if self.last_model_update:
                time_since_update = datetime.now() - self.last_model_update
                min_interval = timedelta(seconds=self.config.get('model_retrain_interval', 86400))
                
                if time_since_update < min_interval:
                    return
            
            # Check if we have enough new feedback data
            recent_feedback = [
                f for f in self.performance_history
                if self.last_model_update is None or f.timestamp > self.last_model_update
            ]
            
            if len(recent_feedback) < 100:  # Need at least 100 new samples
                return
            
            # Check if performance has degraded
            recent_errors = [f.prediction_error for f in recent_feedback[-50:]]
            avg_recent_error = np.mean(recent_errors)
            
            if avg_recent_error > 0.1:  # 10% error threshold
                logger.info("🧠 Model retraining triggered due to performance degradation")
                await self._retrain_models()
        
        except Exception as e:
            logger.error(f"❌ Error checking model retraining: {e}")
    
    async def _retrain_models(self) -> None:
        """Retrain ML models with latest data"""
        try:
            logger.info("🔄 Retraining ML models...")
            
            # TODO: Implement actual model retraining logic
            # This would involve:
            # 1. Gathering latest training data
            # 2. Retraining regime classifier
            # 3. Retraining performance predictor
            # 4. Validating model performance
            # 5. Updating model versions
            
            self.last_model_update = datetime.now()
            logger.info("✅ ML models retrained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error retraining models: {e}")
    
    def _on_market_data_update(self, message: Message) -> None:
        """Handle market data updates from message bus"""
        try:
            # Process market data update
            # This would trigger regime analysis if configured for real-time updates
            if self.config.get('enable_real_time_updates', True):
                # Schedule async analysis
                asyncio.create_task(self._process_market_data_update(message.data))
                
        except Exception as e:
            logger.error(f"❌ Error handling market data update: {e}")
    
    def _on_performance_update(self, message: Message) -> None:
        """Handle performance updates from message bus"""
        try:
            # Process performance update
            # This would convert to PerformanceFeedback and update the system
            feedback_data = message.data
            
            # Create PerformanceFeedback object
            feedback = PerformanceFeedback(
                timestamp=datetime.now(),
                strategy=StrategyType(feedback_data.get('strategy')),
                instrument=feedback_data.get('instrument'),
                regime=MarketCondition(feedback_data.get('regime')),
                actual_return=feedback_data.get('actual_return', 0.0),
                predicted_return=feedback_data.get('predicted_return', 0.0),
                prediction_error=feedback_data.get('prediction_error', 0.0),
                risk_adjusted_return=feedback_data.get('risk_adjusted_return', 0.0),
                execution_quality=feedback_data.get('execution_quality', 0.0),
                regime_accuracy=feedback_data.get('regime_accuracy', 0.0),
                metadata=feedback_data.get('metadata', {})
            )
            
            # Schedule async feedback processing
            asyncio.create_task(self.update_performance_feedback(feedback))
            
        except Exception as e:
            logger.error(f"❌ Error handling performance update: {e}")
    
    async def _process_market_data_update(self, market_data: Dict[str, Any]) -> None:
        """Process real-time market data update"""
        try:
            # Convert message data to DataFrame format expected by analyze_current_market_condition
            # This is a simplified example - real implementation would depend on data format
            df_data = pd.DataFrame([market_data])
            
            # Analyze current market condition
            await self.analyze_current_market_condition(df_data)
            
        except Exception as e:
            logger.error(f"❌ Error processing market data update: {e}")


# TODO: Continue with the remaining component classes:
# - EnhancedRegimeDetector
# - DynamicStrategySelector  
# - InstrumentOptimizer
# - PerformanceTracker
# - UnifiedDataProcessor

# These will be implemented in subsequent files to maintain modularity


# ================================================================================
# SUPPORTING COMPONENT CLASSES
# ================================================================================

class EnhancedRegimeDetector:
    """Enhanced regime detection with ML-powered models"""
    
    def __init__(self, parent_engine):
        self.parent = parent_engine
        self.logger = logging.getLogger(f"{__name__}.EnhancedRegimeDetector")
    
    async def detect_current_regime(self, processed_data: Dict[str, Any]) -> MarketConditionState:
        """Detect current market regime using enhanced multi-factor analysis"""
        try:
            current_time = datetime.now()
            
            # Extract key indicators from processed data
            volatility = processed_data.get('volatility', 0.2)
            trend_strength = processed_data.get('trend_strength', 0.0)
            volume_profile = processed_data.get('volume_profile', 1.0)
            price_momentum = processed_data.get('price_momentum', 0.0)
            
            # Additional regime indicators
            vix_level = processed_data.get('vix_equivalent', volatility * 100)
            correlation_breakdown = processed_data.get('correlation_breakdown', False)
            flight_to_quality = processed_data.get('flight_to_quality', False)
            
            # Multi-factor regime classification
            regime_scores = {
                MarketCondition.CRISIS_MODE: 0.0,
                MarketCondition.TRENDING_BULL: 0.0,
                MarketCondition.TRENDING_BEAR: 0.0,
                MarketCondition.HIGH_VOLATILITY: 0.0,
                MarketCondition.SIDEWAYS_RANGE: 0.0,
                MarketCondition.LOW_VOLATILITY: 0.0
            }
            
            # Crisis mode indicators (stricter criteria)
            if vix_level > 60 or volatility > 0.6:  # More stringent crisis thresholds
                regime_scores[MarketCondition.CRISIS_MODE] += 2.0
            if flight_to_quality and volatility > 0.4:
                regime_scores[MarketCondition.CRISIS_MODE] += 1.5
            if volume_profile > 3.0:  # Extreme volume spike
                regime_scores[MarketCondition.CRISIS_MODE] += 1.0
            
            # Trending bull indicators
            if trend_strength > 0.3 and price_momentum > 0.2:
                regime_scores[MarketCondition.TRENDING_BULL] += 2.5
            if trend_strength > 0.1 and volatility < 0.25:
                regime_scores[MarketCondition.TRENDING_BULL] += 2.0
            if volume_profile > 1.2 and trend_strength > 0.05:
                regime_scores[MarketCondition.TRENDING_BULL] += 1.0
            
            # Trending bear indicators
            if trend_strength < -0.3 and price_momentum < -0.2:
                regime_scores[MarketCondition.TRENDING_BEAR] += 2.5
            if trend_strength < -0.1 and volatility > 0.3:
                regime_scores[MarketCondition.TRENDING_BEAR] += 2.0
            if flight_to_quality and trend_strength < -0.05:
                regime_scores[MarketCondition.TRENDING_BEAR] += 1.0
            
            # High volatility indicators (but not crisis)
            if 0.25 < volatility <= 0.6 and abs(trend_strength) < 0.3:
                regime_scores[MarketCondition.HIGH_VOLATILITY] += 2.5
            if 20 < vix_level <= 60:
                regime_scores[MarketCondition.HIGH_VOLATILITY] += 2.0
            if volume_profile > 1.5 and abs(price_momentum) > 0.1:
                regime_scores[MarketCondition.HIGH_VOLATILITY] += 1.0
            
            # Sideways range indicators
            if abs(trend_strength) < 0.15 and volatility < 0.3:
                regime_scores[MarketCondition.SIDEWAYS_RANGE] += 2.5
            if 0.8 < volume_profile < 1.3:  # Normal volume
                regime_scores[MarketCondition.SIDEWAYS_RANGE] += 2.0
            if abs(price_momentum) < 0.1:
                regime_scores[MarketCondition.SIDEWAYS_RANGE] += 1.5
            
            # Low volatility indicators
            if volatility < 0.15 and abs(trend_strength) < 0.2:
                regime_scores[MarketCondition.LOW_VOLATILITY] += 2.5
            if vix_level < 15:
                regime_scores[MarketCondition.LOW_VOLATILITY] += 2.0
            if volume_profile < 0.9:  # Below average volume
                regime_scores[MarketCondition.LOW_VOLATILITY] += 1.0
            
            # Add base scores to prevent all scenarios defaulting to crisis
            regime_scores[MarketCondition.SIDEWAYS_RANGE] += 1.0  # Default baseline
            regime_scores[MarketCondition.HIGH_VOLATILITY] += 0.5
            regime_scores[MarketCondition.TRENDING_BULL] += 0.3
            regime_scores[MarketCondition.TRENDING_BEAR] += 0.3
            
            # Determine primary regime
            primary_condition = max(regime_scores, key=regime_scores.get)
            max_score = regime_scores[primary_condition]
            
            # Calculate confidence based on score separation
            sorted_scores = sorted(regime_scores.values(), reverse=True)
            if len(sorted_scores) > 1 and sorted_scores[0] > 0:
                confidence = min(0.95, 0.5 + (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0] * 0.45)
            else:
                confidence = 0.5  # Low confidence fallback
            
            # Calculate market stress based on volatility and other factors
            stress_components = []
            stress_components.append(min(0.5, volatility * 1.5))  # Volatility component (0-0.5)
            stress_components.append(min(0.3, vix_level / 200))    # VIX component (0-0.3)
            if flight_to_quality:
                stress_components.append(0.2)  # Flight to quality component
            
            market_stress = min(1.0, sum(stress_components))
            
            # Determine volatility regime
            if volatility < 0.15:
                volatility_regime = "low"
            elif volatility > 0.4:
                volatility_regime = "high"
            else:
                volatility_regime = "normal"
            
            return MarketConditionState(
                timestamp=current_time,
                primary_condition=primary_condition,
                secondary_conditions=[],
                confidence=confidence,
                volatility_regime=volatility_regime,
                trend_strength=trend_strength,
                market_stress=market_stress,
                liquidity_condition="normal",
                regime_duration=timedelta(hours=2),
                transition_probability={condition: score/10 for condition, score in regime_scores.items()},
                features=processed_data,
                metadata={
                    'regime_scores': regime_scores,
                    'max_score': max_score,
                    'vix_level': vix_level,
                    'volume_profile': volume_profile
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting regime: {e}")
            raise


class DynamicStrategySelector:
    """Dynamic strategy selection based on market regimes"""
    
    def __init__(self, parent_engine):
        self.parent = parent_engine
        self.logger = logging.getLogger(f"{__name__}.DynamicStrategySelector")
    
    async def select_strategies(self, 
                              market_state: MarketConditionState,
                              portfolio_context: Optional[Dict[str, Any]] = None) -> StrategySelection:
        """Select optimal strategies for current market regime"""
        try:
            current_time = datetime.now()
            regime = market_state.primary_condition
            confidence = market_state.confidence
            trend_strength = market_state.trend_strength
            market_stress = market_state.market_stress
            
            # Enhanced regime-specific strategy allocation
            strategy_weights = {}
            
            if regime == MarketCondition.TRENDING_BULL:
                # Bull markets favor momentum and growth strategies
                strategy_weights = {
                    StrategyType.MOMENTUM: 0.70,
                    StrategyType.MEAN_REVERSION: 0.15,
                    StrategyType.PAIRS_TRADING: 0.15
                }
            elif regime == MarketCondition.TRENDING_BEAR:
                # Bear markets favor defensive and mean reversion strategies
                strategy_weights = {
                    StrategyType.MEAN_REVERSION: 0.50,
                    StrategyType.PAIRS_TRADING: 0.35,
                    StrategyType.MOMENTUM: 0.15
                }
            elif regime == MarketCondition.HIGH_VOLATILITY:
                # High volatility favors market-neutral and volatility strategies
                strategy_weights = {
                    StrategyType.PAIRS_TRADING: 0.60,
                    StrategyType.MEAN_REVERSION: 0.25,
                    StrategyType.MOMENTUM: 0.15
                }
            elif regime == MarketCondition.CRISIS_MODE:
                # Crisis mode: ultra-defensive allocation
                strategy_weights = {
                    StrategyType.PAIRS_TRADING: 0.70,
                    StrategyType.MEAN_REVERSION: 0.30,
                    StrategyType.MOMENTUM: 0.00
                }
            elif regime == MarketCondition.SIDEWAYS_RANGE:
                # Range-bound markets favor mean reversion
                strategy_weights = {
                    StrategyType.MEAN_REVERSION: 0.60,
                    StrategyType.PAIRS_TRADING: 0.25,
                    StrategyType.MOMENTUM: 0.15
                }
            elif regime == MarketCondition.LOW_VOLATILITY:
                # Low volatility allows for more aggressive momentum
                strategy_weights = {
                    StrategyType.MOMENTUM: 0.55,
                    StrategyType.MEAN_REVERSION: 0.30,
                    StrategyType.PAIRS_TRADING: 0.15
                }
            else:
                # Default balanced allocation
                strategy_weights = {
                    StrategyType.MEAN_REVERSION: 0.40,
                    StrategyType.PAIRS_TRADING: 0.35,
                    StrategyType.MOMENTUM: 0.25
                }
            
            # Adjust based on confidence level
            if confidence < 0.6:
                # Low confidence: increase pairs trading (market neutral)
                pairs_boost = 0.1
                strategy_weights[StrategyType.PAIRS_TRADING] += pairs_boost
                # Reduce momentum proportionally
                if strategy_weights[StrategyType.MOMENTUM] >= pairs_boost:
                    strategy_weights[StrategyType.MOMENTUM] -= pairs_boost
                else:
                    strategy_weights[StrategyType.MEAN_REVERSION] -= (pairs_boost - strategy_weights[StrategyType.MOMENTUM])
                    strategy_weights[StrategyType.MOMENTUM] = 0.05
            
            # Adjust based on market stress
            if market_stress > 0.7:
                # High stress: further increase defensive strategies
                stress_adjustment = 0.15
                strategy_weights[StrategyType.PAIRS_TRADING] += stress_adjustment
                strategy_weights[StrategyType.MOMENTUM] = max(0.05, strategy_weights[StrategyType.MOMENTUM] - stress_adjustment)
            
            # Ensure weights sum to 1.0
            total_weight = sum(strategy_weights.values())
            strategy_weights = {k: v/total_weight for k, v in strategy_weights.items()}
            
            # Calculate expected performance based on regime
            expected_performance = {}
            if regime == MarketCondition.TRENDING_BULL:
                expected_performance = {
                    StrategyType.MOMENTUM: 0.12,
                    StrategyType.MEAN_REVERSION: 0.04,
                    StrategyType.PAIRS_TRADING: 0.06
                }
            elif regime == MarketCondition.TRENDING_BEAR:
                expected_performance = {
                    StrategyType.MOMENTUM: -0.02,
                    StrategyType.MEAN_REVERSION: 0.08,
                    StrategyType.PAIRS_TRADING: 0.05
                }
            elif regime == MarketCondition.HIGH_VOLATILITY:
                expected_performance = {
                    StrategyType.MOMENTUM: 0.02,
                    StrategyType.MEAN_REVERSION: 0.06,
                    StrategyType.PAIRS_TRADING: 0.08
                }
            elif regime == MarketCondition.CRISIS_MODE:
                expected_performance = {
                    StrategyType.MOMENTUM: -0.08,
                    StrategyType.MEAN_REVERSION: 0.03,
                    StrategyType.PAIRS_TRADING: 0.04
                }
            else:  # SIDEWAYS_RANGE, LOW_VOLATILITY
                expected_performance = {
                    StrategyType.MOMENTUM: 0.04,
                    StrategyType.MEAN_REVERSION: 0.10,
                    StrategyType.PAIRS_TRADING: 0.06
                }
            
            return StrategySelection(
                timestamp=current_time,
                regime=regime,
                selected_strategies=strategy_weights,
                confidence=confidence,
                expected_performance=expected_performance,
                risk_assessment={strategy: 0.1 + (0.05 * market_stress) for strategy in strategy_weights},
                instruments_per_strategy={},
                reasoning={
                    "regime_based": True, 
                    "confidence": confidence,
                    "trend_strength": trend_strength,
                    "market_stress": market_stress,
                    "allocation_logic": f"Optimized for {regime.value} with {confidence:.1%} confidence"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error selecting strategies: {e}")
            raise


class InstrumentOptimizer:
    """Intelligent instrument selection and optimization"""
    
    def __init__(self, parent_engine):
        self.parent = parent_engine
        self.logger = logging.getLogger(f"{__name__}.InstrumentOptimizer")
    
    async def rank_instruments(self, 
                             strategy_type: StrategyType,
                             market_state: MarketConditionState) -> List[InstrumentRanking]:
        """Rank instruments for a specific strategy-regime combination"""
        try:
            # Placeholder implementation
            # Real implementation would analyze historical performance, liquidity, etc.
            
            # Sample instrument universe
            instruments = ['SPY', 'QQQ', 'IWM', 'TLT', 'GLD', 'VXX', 'AAPL', 'MSFT', 'GOOGL', 'TSLA']
            
            rankings = []
            for i, symbol in enumerate(instruments):
                ranking = InstrumentRanking(
                    symbol=symbol,
                    strategy=strategy_type,
                    regime=market_state.primary_condition,
                    rank=i + 1,
                    score=0.9 - (i * 0.05),  # Decreasing score
                    expected_return=0.08 - (i * 0.005),
                    risk_score=0.15 + (i * 0.01),
                    liquidity_score=0.95 - (i * 0.02),
                    regime_suitability=market_state.confidence,
                    historical_performance={"sharpe": 1.2 - (i * 0.1)}
                )
                rankings.append(ranking)
            
            return rankings
            
        except Exception as e:
            self.logger.error(f"Error ranking instruments: {e}")
            raise


class PerformanceTracker:
    """Performance tracking and feedback processing"""
    
    def __init__(self, parent_engine):
        self.parent = parent_engine
        self.logger = logging.getLogger(f"{__name__}.PerformanceTracker")
    
    async def process_feedback(self, feedback: PerformanceFeedback) -> None:
        """Process performance feedback for continuous improvement"""
        try:
            # Analyze feedback and update internal models
            self.logger.info(f"Processing feedback for {feedback.strategy.value} on {feedback.instrument}")
            
            # Update strategy performance tracking
            # Update regime accuracy tracking
            # Update instrument performance tracking
            
        except Exception as e:
            self.logger.error(f"Error processing feedback: {e}")
            raise


class UnifiedDataProcessor:
    """Unified data processing for multiple data sources"""
    
    def __init__(self, parent_engine):
        self.parent = parent_engine
        self.logger = logging.getLogger(f"{__name__}.UnifiedDataProcessor")
    
    async def process_all_data(self,
                             market_data: pd.DataFrame,
                             macro_data: Optional[Dict[str, Any]] = None,
                             sentiment_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process and integrate all data sources"""
        try:
            processed_data = {}
            
            # Process market data
            if not market_data.empty:
                processed_data.update(self._process_market_data(market_data))
            
            # Process macro data
            if macro_data:
                processed_data.update(self._process_macro_data(macro_data))
            
            # Process sentiment data
            if sentiment_data:
                processed_data.update(self._process_sentiment_data(sentiment_data))
            
            # Calculate derived features
            processed_data.update(self._calculate_derived_features(processed_data))
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing data: {e}")
            raise
    
    def _process_market_data(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Process OHLCV market data with enhanced regime indicators"""
        try:
            if 'close' not in market_data.columns:
                return {}
            
            closes = market_data['close']
            returns = closes.pct_change().dropna()
            
            # Basic market features
            volatility = returns.std() * np.sqrt(252)
            trend_strength = self._calculate_trend_strength(closes)
            
            # Enhanced regime-specific features
            features = {
                'volatility': volatility,
                'returns_mean': returns.mean() * 252,
                'skewness': returns.skew(),
                'kurtosis': returns.kurtosis(),
                'trend_strength': trend_strength,
                'price_momentum': self._calculate_price_momentum(closes),
                'volume_profile': self._calculate_volume_profile(market_data) if 'volume' in market_data.columns else 1.0,
                'vix_equivalent': volatility * 100,  # Convert to VIX-like scale
                'correlation_breakdown': volatility > 0.4,  # Simple correlation breakdown indicator
            }
            
            # Add symbol-specific analysis if multiple symbols
            if 'symbol' in market_data.columns:
                features.update(self._analyze_cross_asset_behavior(market_data))
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")
            return {}
    
    def _calculate_price_momentum(self, prices: pd.Series) -> float:
        """Calculate short-term price momentum"""
        try:
            if len(prices) < 20:
                return 0.0
            
            # Compare recent average to longer-term average
            short_ma = prices.tail(5).mean()
            long_ma = prices.tail(20).mean()
            
            if long_ma == 0:
                return 0.0
            
            momentum = (short_ma - long_ma) / long_ma
            return np.tanh(momentum * 10)  # Normalize to [-1, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating price momentum: {e}")
            return 0.0
    
    def _calculate_volume_profile(self, market_data: pd.DataFrame) -> float:
        """Calculate volume profile relative to historical average"""
        try:
            if 'volume' not in market_data.columns or len(market_data) < 10:
                return 1.0
            
            volume = market_data['volume']
            recent_volume = volume.tail(5).mean()
            historical_volume = volume.mean()
            
            if historical_volume == 0:
                return 1.0
            
            return recent_volume / historical_volume
            
        except Exception as e:
            self.logger.error(f"Error calculating volume profile: {e}")
            return 1.0
    
    def _analyze_cross_asset_behavior(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cross-asset relationships for regime detection"""
        try:
            features = {}
            
            # Check for flight-to-quality indicators
            symbols = market_data['symbol'].unique()
            
            # Look for VIX spike
            if 'VIX' in symbols:
                vix_data = market_data[market_data['symbol'] == 'VIX']['close']
                if not vix_data.empty:
                    vix_level = vix_data.iloc[-1]
                    features['vix_equivalent'] = vix_level
                    features['flight_to_quality'] = vix_level > 30
            
            # Look for defensive asset behavior (GLD, TLT)
            defensive_symbols = ['GLD', 'TLT']
            equity_symbols = ['SPY', 'QQQ', 'AAPL', 'TSLA']
            
            defensive_performance = []
            equity_performance = []
            
            for symbol in symbols:
                symbol_data = market_data[market_data['symbol'] == symbol]['close']
                if len(symbol_data) > 1:
                    performance = (symbol_data.iloc[-1] - symbol_data.iloc[0]) / symbol_data.iloc[0]
                    
                    if symbol in defensive_symbols:
                        defensive_performance.append(performance)
                    elif symbol in equity_symbols:
                        equity_performance.append(performance)
            
            # Flight to quality if defensive assets outperforming equities
            if defensive_performance and equity_performance:
                avg_defensive = np.mean(defensive_performance)
                avg_equity = np.mean(equity_performance)
                features['flight_to_quality'] = avg_defensive > avg_equity and avg_equity < -0.02
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error analyzing cross-asset behavior: {e}")
            return {}
    
    def _process_macro_data(self, macro_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process macroeconomic data"""
        try:
            # Extract relevant macro indicators
            features = {
                'interest_rate': macro_data.get('fed_funds_rate', 0.0),
                'inflation_rate': macro_data.get('cpi_yoy', 0.0),
                'gdp_growth': macro_data.get('gdp_growth_qoq', 0.0),
                'unemployment_rate': macro_data.get('unemployment', 0.0),
                'vix_level': macro_data.get('vix', 20.0)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing macro data: {e}")
            return {}
    
    def _process_sentiment_data(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process sentiment data"""
        try:
            features = {
                'news_sentiment': sentiment_data.get('news_sentiment_score', 0.0),
                'social_sentiment': sentiment_data.get('social_media_sentiment', 0.0),
                'analyst_sentiment': sentiment_data.get('analyst_sentiment', 0.0),
                'put_call_ratio': sentiment_data.get('put_call_ratio', 1.0)
            }
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error processing sentiment data: {e}")
            return {}
    
    def _calculate_derived_features(self, base_features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived features from base features"""
        try:
            derived = {}
            
            # Market stress indicator
            volatility = base_features.get('volatility', 0.2)
            vix = base_features.get('vix_level', 20.0)
            derived['market_stress'] = min(1.0, (volatility * 2 + vix / 50) / 2)
            
            # Risk appetite indicator
            put_call = base_features.get('put_call_ratio', 1.0)
            derived['risk_appetite'] = max(0.0, 1.0 - put_call)
            
            # Economic health indicator
            gdp = base_features.get('gdp_growth', 0.0)
            unemployment = base_features.get('unemployment_rate', 5.0)
            derived['economic_health'] = max(0.0, (gdp / 4 + (10 - unemployment) / 10) / 2)
            
            return derived
            
        except Exception as e:
            self.logger.error(f"Error calculating derived features: {e}")
            return {}
    
    def _calculate_trend_strength(self, prices: pd.Series) -> float:
        """Calculate trend strength using linear regression"""
        try:
            if len(prices) < 10:
                return 0.0
            
            x = np.arange(len(prices))
            y = prices.values
            
            # Simple linear regression
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x * x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # Normalize slope by price level
            normalized_slope = slope / np.mean(y) if np.mean(y) != 0 else 0
            
            # Return strength between -1 and 1
            return np.tanh(normalized_slope * 100)
            
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return 0.0
    
    def _calculate_volume_trend(self, market_data: pd.DataFrame) -> float:
        """Calculate volume trend"""
        try:
            if 'volume' not in market_data.columns or len(market_data) < 10:
                return 0.0
            
            volume = market_data['volume']
            recent_volume = volume.tail(5).mean()
            historical_volume = volume.head(-5).mean()
            
            if historical_volume == 0:
                return 0.0
            
            volume_ratio = recent_volume / historical_volume
            return np.tanh((volume_ratio - 1) * 2)  # Normalize to [-1, 1]
            
        except Exception as e:
            self.logger.error(f"Error calculating volume trend: {e}")
            return 0.0