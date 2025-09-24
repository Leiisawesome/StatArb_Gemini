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
        
        # ML-based transition prediction components
        self.transition_scaler = StandardScaler()
        self.transition_models = {
            "1H": RandomForestClassifier(n_estimators=100, random_state=42),
            "1D": GradientBoostingClassifier(n_estimators=100, random_state=42),
            "1W": RandomForestClassifier(n_estimators=50, random_state=42)
        }
        self.transition_history = []  # Historical transitions for training
        self.models_trained = False
        self.feature_history = []  # Feature vectors for ML training
        
        # Core engine regime components (self-contained)
        # self.config = config or RegimeConfig()
        # self.current_regime = MarketRegime.SIDEWAYS
        # self.regime_confidence = 0.0
        
        # State
        self.is_initialized = False
        self.is_running = False
        self.regime_analysis_task: Optional[asyncio.Task] = None
        
        logger.info("🎯 Regime Engine initialized for core engine with multi-timeframe support")
    
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
            # Handle both dict and object formats
            if isinstance(data, dict):
                symbol = data.get('symbol')
                price = data.get('close')
            else:
                symbol = getattr(data, 'symbol', None)
                price = getattr(data, 'close', None)
            
            if not symbol or price is None:
                logger.debug(f"Invalid market data format: {data}")
                return
            
            # Update price buffer
            if symbol not in self.market_data_buffer:
                self.market_data_buffer[symbol] = []
            
            self.market_data_buffer[symbol].append(float(price))
            
            # Keep only recent data
            max_buffer_size = max(self.config.lookback_window, self.config.volatility_window) * 2
            if len(self.market_data_buffer[symbol]) > max_buffer_size:
                self.market_data_buffer[symbol] = self.market_data_buffer[symbol][-max_buffer_size:]
            
            # Update multi-timeframe buffers
            await self._update_timeframe_buffers(symbol, float(price))
            
        except Exception as e:
            logger.debug(f"Failed to process market data in regime engine: {e}")
    
    async def get_current_regime(self) -> Optional[RegimeAnalysis]:
        """Get current regime analysis"""
        return self.current_regime
    
    async def get_current_regime_info(self) -> Dict[str, Any]:
        """
        Get current regime information in format expected by other components
        ENHANCED: Compatible with Strategy Manager and Risk Manager expectations
        """
        if not self.current_regime:
            # Return default regime info
            return {
                'regime': 'neutral',
                'confidence': 0.5,
                'volatility': 0.02,
                'trend_strength': 0.0,
                'risk_multiplier': 1.0,
                'recommended_strategies': ['mean_reversion', 'momentum'],
                'strategy_weights': {'mean_reversion': 0.5, 'momentum': 0.5}
            }
        
        # Map regime analysis to expected format
        regime_name = self._map_regime_to_string(self.current_regime.primary_regime)
        
        # Calculate risk multiplier based on regime
        risk_multiplier = self._calculate_risk_multiplier(regime_name, self.current_regime.volatility_regime)
        
        # Get recommended strategies
        recommended_strategies = self._get_recommended_strategies(self.current_regime.strategy_suitability)
        
        # Convert strategy suitability to weights
        strategy_weights = self._normalize_strategy_weights(self.current_regime.strategy_suitability)
        
        return {
            'regime': regime_name,
            'confidence': self.current_regime.confidence,
            'volatility': self._extract_volatility_value(self.current_regime.volatility_regime),
            'trend_strength': self.current_regime.trend_strength,
            'risk_multiplier': risk_multiplier,
            'recommended_strategies': recommended_strategies,
            'strategy_weights': strategy_weights,
            'regime_duration': self.current_regime.regime_duration,
            'timestamp': self.current_regime.timestamp
        }
    
    def _map_regime_to_string(self, regime: MarketRegime) -> str:
        """Map MarketRegime enum to string format expected by components"""
        regime_mapping = {
            MarketRegime.BULL_MARKET: 'trending_up',
            MarketRegime.BEAR_MARKET: 'trending_down',
            MarketRegime.TRENDING: 'trending',
            MarketRegime.MEAN_REVERTING: 'ranging',
            MarketRegime.HIGH_VOLATILITY: 'volatile',
            MarketRegime.LOW_VOLATILITY: 'calm',
            MarketRegime.SIDEWAYS: 'sideways'
        }
        return regime_mapping.get(regime, 'neutral')
    
    def _calculate_risk_multiplier(self, regime: str, volatility_regime: str) -> float:
        """Calculate risk multiplier based on regime and volatility"""
        base_multipliers = {
            'trending_up': 0.9,
            'trending_down': 1.2,
            'trending': 1.0,
            'ranging': 0.8,
            'volatile': 1.6,
            'calm': 0.7,
            'sideways': 1.0,
            'neutral': 1.0
        }
        
        base_multiplier = base_multipliers.get(regime, 1.0)
        
        # Adjust for volatility
        if volatility_regime == 'high_volatility':
            base_multiplier *= 1.3
        elif volatility_regime == 'low_volatility':
            base_multiplier *= 0.8
        
        return round(base_multiplier, 2)
    
    def _get_recommended_strategies(self, strategy_suitability: Dict[str, float]) -> List[str]:
        """Get list of recommended strategies based on suitability scores"""
        # Sort strategies by suitability score
        sorted_strategies = sorted(strategy_suitability.items(), key=lambda x: x[1], reverse=True)
        
        # Return strategies with suitability > 0.6
        recommended = [strategy for strategy, score in sorted_strategies if score > 0.6]
        
        # Always return at least one strategy
        if not recommended:
            recommended = [sorted_strategies[0][0]]
        
        return recommended
    
    def _normalize_strategy_weights(self, strategy_suitability: Dict[str, float]) -> Dict[str, float]:
        """Normalize strategy suitability scores to weights that sum to 1"""
        total_score = sum(strategy_suitability.values())
        
        if total_score == 0:
            # Equal weights if no suitability data
            num_strategies = len(strategy_suitability)
            return {strategy: 1.0 / num_strategies for strategy in strategy_suitability}
        
        # Normalize to sum to 1
        weights = {strategy: score / total_score for strategy, score in strategy_suitability.items()}
        
        return weights
    
    def _extract_volatility_value(self, volatility_regime: str) -> float:
        """Extract numeric volatility value from regime string"""
        volatility_values = {
            'high_volatility': 0.04,
            'normal_volatility': 0.02,
            'low_volatility': 0.01
        }
        return volatility_values.get(volatility_regime, 0.02)
    
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
        """
        Perform comprehensive regime analysis
        ENHANCED: Advanced regime detection from test implementation
        """
        # Use the primary market symbol (e.g., SPY) for regime analysis
        primary_symbol = list(self.market_data_buffer.keys())[0] if self.market_data_buffer else None
        
        if not primary_symbol:
            raise ValueError("No market data available for regime analysis")
        
        prices = np.array(self.market_data_buffer[primary_symbol])
        
        if len(prices) < 20:
            # Default regime for insufficient data
            return RegimeAnalysis(
                primary_regime=MarketRegime.SIDEWAYS,
                confidence=0.5,
                volatility_regime="normal",
                trend_strength=0.0,
                regime_duration=1,
                strategy_suitability={'momentum': 0.5, 'mean_reversion': 0.5},
                timestamp=datetime.now()
            )
        
        # Enhanced regime analysis from test implementation
        regime_analysis = await self._perform_enhanced_regime_analysis(prices)
        
        return regime_analysis
    
    async def _perform_enhanced_regime_analysis(self, prices: np.ndarray) -> RegimeAnalysis:
        """
        Advanced Professional Regime Analysis - Tier 2 Enhanced
        Supports 15+ granular regime states with sophisticated detection
        """
        try:
            # === MULTI-TIMEFRAME REGIME ANALYSIS ===
            timeframe_regimes = await self._analyze_multi_timeframe_regimes()
            regime_consensus = self._calculate_regime_consensus(timeframe_regimes)
            dominant_timeframe = self._determine_dominant_timeframe(timeframe_regimes)
            
            # === SINGLE-TIMEFRAME ANALYSIS (Legacy) ===
            recent_returns = np.diff(prices[-20:]) / prices[-20:-1]
            medium_returns = np.diff(prices[-60:]) / prices[-60:-1] if len(prices) >= 60 else recent_returns
            
            # === VOLATILITY ANALYSIS ===
            short_vol = np.std(recent_returns) * np.sqrt(252)  # 20-period volatility
            medium_vol = np.std(medium_returns) * np.sqrt(252)  # 60-period volatility
            vol_of_vol = np.std([np.std(recent_returns[i:i+5]) for i in range(0, len(recent_returns)-5, 5)])
            
            # === TREND ANALYSIS ===
            current_price = prices[-1]
            sma_20 = np.mean(prices[-20:])
            sma_60 = np.mean(prices[-60:]) if len(prices) >= 60 else sma_20
            
            short_trend = (current_price - sma_20) / sma_20
            medium_trend = (current_price - sma_60) / sma_60
            trend_consistency = np.corrcoef(prices[-20:], np.arange(20))[0, 1] if len(prices) >= 20 else 0
            
            # === STRESS ANALYSIS ===
            max_drawdown = self._calculate_max_drawdown(prices[-60:]) if len(prices) >= 60 else 0
            stress_level = min(1.0, max_drawdown * 10 + short_vol * 2)
            
            # === ADVANCED REGIME CLASSIFICATION ===
            primary_regime, regime_components = self._classify_advanced_regime(
                short_vol, medium_vol, short_trend, medium_trend, trend_consistency, stress_level, vol_of_vol
            )
            
            # === CONFIDENCE CALCULATION ===
            confidence = self._calculate_advanced_confidence(
                short_vol, medium_vol, trend_consistency, stress_level, len(prices)
            )
            
            # === REGIME CHARACTERISTICS ===
            regime_stability = max(0.0, 1.0 - vol_of_vol * 50)  # Lower vol-of-vol = more stable
            transition_probability = self._calculate_transition_probability(
                short_vol, medium_vol, trend_consistency, regime_stability
            )
            regime_maturity = min(1.0, self._calculate_regime_duration() / 30.0)  # Mature after 30 periods
            
            # === STRATEGY IMPLICATIONS ===
            strategy_suitability = self._calculate_advanced_strategy_suitability(
                primary_regime, regime_components, short_vol, short_trend
            )
            risk_adjustment = self._calculate_risk_adjustment(stress_level, short_vol)
            position_sizing_factor = self._calculate_position_sizing_factor(primary_regime, short_vol, confidence)
            
            # === REGIME DRIVERS ===
            regime_drivers = self._identify_regime_drivers(
                short_vol, medium_vol, short_trend, medium_trend, stress_level
            )
            
            # Create preliminary analysis for ML prediction
            preliminary_analysis = RegimeAnalysis(
                primary_regime=primary_regime,
                confidence=confidence,
                regime_duration=self._calculate_regime_duration(),
                timestamp=datetime.now(),
                
                # Detailed regime components
                directional_regime=regime_components['directional'],
                volatility_regime=regime_components['volatility'],
                trend_strength=abs(short_trend),
                stress_level=stress_level,
                liquidity_regime=regime_components['liquidity'],
                
                # Regime characteristics
                regime_stability=regime_stability,
                transition_probability=transition_probability,
                regime_maturity=regime_maturity,
                
                # Multi-timeframe regime analysis
                timeframe_regimes=timeframe_regimes,
                regime_consensus=regime_consensus,
                dominant_timeframe=dominant_timeframe,
                
                # Strategy implications
                strategy_suitability=strategy_suitability,
                risk_adjustment=risk_adjustment,
                position_sizing_factor=position_sizing_factor,
                
                # Regime context
                sub_regimes=regime_components,
                regime_drivers=regime_drivers,
                regime_outlook=self._determine_regime_outlook(transition_probability, regime_maturity)
            )
            
            # === ML-BASED TRANSITION PREDICTIONS ===
            transition_predictions = await self._predict_regime_transitions(preliminary_analysis)
            
            # Calculate ML-enhanced transition probability
            ml_transition_prob = self._calculate_ml_transition_probability(transition_predictions)
            transition_confidence = self._calculate_transition_confidence(transition_predictions)
            predicted_next_regime = self._determine_most_likely_next_regime(transition_predictions)
            
            # Update analysis with ML predictions
            preliminary_analysis.transition_predictions = transition_predictions
            preliminary_analysis.ml_transition_probability = ml_transition_prob
            preliminary_analysis.transition_confidence = transition_confidence
            preliminary_analysis.predicted_next_regime = predicted_next_regime
            
            return preliminary_analysis
            
        except Exception as e:
            logger.error(f"❌ Advanced regime analysis failed: {e}")
            # Fallback to basic analysis
            return self._perform_basic_regime_analysis(prices)
    
    def _classify_advanced_regime(self, short_vol: float, medium_vol: float, short_trend: float, 
                                medium_trend: float, trend_consistency: float, stress_level: float, 
                                vol_of_vol: float) -> tuple[MarketRegime, Dict[str, str]]:
        """Classify regime using advanced 15+ state system"""
        
        # === DETERMINE DIRECTIONAL REGIME ===
        if short_trend > 0.02 and medium_trend > 0.01:
            directional = "bull"
        elif short_trend < -0.02 and medium_trend < -0.01:
            directional = "bear"
        else:
            directional = "sideways"
        
        # === DETERMINE VOLATILITY REGIME ===
        if short_vol > 0.25:
            volatility = "extreme"
        elif short_vol > 0.15:
            volatility = "high"
        elif short_vol < 0.08:
            volatility = "low"
        else:
            volatility = "normal"
        
        # === DETERMINE LIQUIDITY REGIME ===
        if vol_of_vol > 0.05:
            liquidity = "poor"
        elif vol_of_vol < 0.02:
            liquidity = "abundant"
        else:
            liquidity = "normal"
        
        # === CLASSIFY PRIMARY REGIME ===
        if stress_level > 0.7:
            if directional == "bear":
                primary_regime = MarketRegime.CRISIS_MODE
            else:
                primary_regime = MarketRegime.LIQUIDITY_CRUNCH
        elif stress_level < 0.1 and volatility == "low":
            if directional == "bull":
                primary_regime = MarketRegime.EUPHORIA_MODE
            else:
                primary_regime = MarketRegime.COMPLACENCY_MODE
        elif abs(trend_consistency) > 0.7:
            if volatility in ["high", "extreme"]:
                if directional == "bull":
                    primary_regime = MarketRegime.BULL_HIGH_VOL
                elif directional == "bear":
                    primary_regime = MarketRegime.BEAR_HIGH_VOL
                else:
                    primary_regime = MarketRegime.CHOPPY
            else:
                if directional == "bull":
                    primary_regime = MarketRegime.BULL_LOW_VOL
                elif directional == "bear":
                    primary_regime = MarketRegime.BEAR_LOW_VOL
                else:
                    primary_regime = MarketRegime.RANGE_BOUND
        elif abs(trend_consistency) > 0.4:
            if abs(short_trend) > 0.01:
                primary_regime = MarketRegime.WEAK_TRENDING
            else:
                primary_regime = MarketRegime.RANGE_BOUND
        elif liquidity == "poor":
            primary_regime = MarketRegime.LIQUIDITY_CRUNCH
        elif liquidity == "abundant" and volatility == "low":
            primary_regime = MarketRegime.HIGH_LIQUIDITY
        else:
            # Default classifications
            if abs(trend_consistency) > 0.5:
                primary_regime = MarketRegime.STRONG_TRENDING
            else:
                primary_regime = MarketRegime.CHOPPY
        
        regime_components = {
            'directional': directional,
            'volatility': volatility,
            'liquidity': liquidity,
            'stress': 'high' if stress_level > 0.5 else 'normal' if stress_level > 0.2 else 'low'
        }
        
        return primary_regime, regime_components
    
    def _calculate_advanced_confidence(self, short_vol: float, medium_vol: float, 
                                     trend_consistency: float, stress_level: float, 
                                     data_points: int) -> float:
        """Calculate confidence in regime classification"""
        
        # Base confidence from data sufficiency
        data_confidence = min(1.0, data_points / 100.0)
        
        # Consistency confidence
        consistency_confidence = abs(trend_consistency)
        
        # Volatility confidence (moderate volatility = higher confidence)
        vol_confidence = 1.0 - min(1.0, abs(short_vol - 0.12) * 5)
        
        # Stress confidence (extreme stress = lower confidence)
        stress_confidence = 1.0 - stress_level * 0.3
        
        # Combined confidence
        confidence = (
            data_confidence * 0.3 +
            consistency_confidence * 0.3 +
            vol_confidence * 0.2 +
            stress_confidence * 0.2
        )
        
        return np.clip(confidence, 0.1, 0.95)
    
    def _calculate_transition_probability(self, short_vol: float, medium_vol: float, 
                                       trend_consistency: float, regime_stability: float) -> float:
        """Calculate probability of regime transition"""
        
        # Volatility change indicates potential transition
        vol_change = abs(short_vol - medium_vol) / medium_vol if medium_vol > 0 else 0
        
        # Low trend consistency suggests transition
        consistency_factor = 1.0 - abs(trend_consistency)
        
        # Low stability suggests transition
        stability_factor = 1.0 - regime_stability
        
        transition_prob = (
            vol_change * 0.4 +
            consistency_factor * 0.3 +
            stability_factor * 0.3
        )
        
        return np.clip(transition_prob, 0.0, 1.0)
    
    def _calculate_advanced_strategy_suitability(self, primary_regime: MarketRegime, 
                                               regime_components: Dict[str, str], 
                                               volatility: float, trend: float) -> Dict[str, float]:
        """Calculate strategy suitability for advanced regime states"""
        
        suitability = {
            'momentum': 0.5,
            'mean_reversion': 0.5,
            'trend_following': 0.5,
            'pairs_trading': 0.5,
            'volatility_trading': 0.5
        }
        
        # Regime-specific adjustments
        if primary_regime in [MarketRegime.BULL_LOW_VOL, MarketRegime.BEAR_LOW_VOL]:
            suitability['trend_following'] = 0.8
            suitability['momentum'] = 0.7
            suitability['mean_reversion'] = 0.3
        elif primary_regime in [MarketRegime.BULL_HIGH_VOL, MarketRegime.BEAR_HIGH_VOL]:
            suitability['volatility_trading'] = 0.8
            suitability['momentum'] = 0.6
            suitability['trend_following'] = 0.4
        elif primary_regime == MarketRegime.RANGE_BOUND:
            suitability['mean_reversion'] = 0.8
            suitability['pairs_trading'] = 0.7
            suitability['trend_following'] = 0.2
        elif primary_regime == MarketRegime.CRISIS_MODE:
            suitability['momentum'] = 0.3
            suitability['trend_following'] = 0.2
            suitability['mean_reversion'] = 0.6
            suitability['pairs_trading'] = 0.4
        elif primary_regime == MarketRegime.EUPHORIA_MODE:
            suitability['momentum'] = 0.8
            suitability['trend_following'] = 0.7
            suitability['mean_reversion'] = 0.2
        
        return suitability
    
    def _calculate_risk_adjustment(self, stress_level: float, volatility: float) -> float:
        """Calculate risk adjustment factor"""
        
        # Higher stress = higher risk adjustment
        stress_adjustment = 1.0 + stress_level * 0.5
        
        # Higher volatility = higher risk adjustment
        vol_adjustment = 1.0 + max(0, (volatility - 0.12) * 2)
        
        return min(2.0, stress_adjustment * vol_adjustment)
    
    def _calculate_position_sizing_factor(self, regime: MarketRegime, volatility: float, 
                                        confidence: float) -> float:
        """Calculate position sizing adjustment factor"""
        
        base_factor = 1.0
        
        # Regime-based adjustments
        if regime in [MarketRegime.CRISIS_MODE, MarketRegime.LIQUIDITY_CRUNCH]:
            base_factor = 0.5  # Reduce positions in crisis
        elif regime in [MarketRegime.EUPHORIA_MODE, MarketRegime.BULL_LOW_VOL]:
            base_factor = 1.2  # Increase positions in favorable conditions
        elif regime == MarketRegime.CHOPPY:
            base_factor = 0.7  # Reduce positions in choppy markets
        
        # Volatility adjustment
        vol_factor = max(0.3, 1.0 - (volatility - 0.12) * 2)
        
        # Confidence adjustment
        confidence_factor = 0.5 + confidence * 0.5
        
        return base_factor * vol_factor * confidence_factor
    
    def _identify_regime_drivers(self, short_vol: float, medium_vol: float, 
                               short_trend: float, medium_trend: float, 
                               stress_level: float) -> List[str]:
        """Identify key drivers of current regime"""
        
        drivers = []
        
        if abs(short_trend) > 0.02:
            drivers.append("strong_directional_move")
        if short_vol > 0.2:
            drivers.append("high_volatility")
        if stress_level > 0.5:
            drivers.append("market_stress")
        if abs(short_vol - medium_vol) > 0.05:
            drivers.append("volatility_regime_change")
        if abs(short_trend - medium_trend) > 0.03:
            drivers.append("trend_acceleration")
        
        return drivers if drivers else ["normal_market_conditions"]
    
    def _determine_regime_outlook(self, transition_probability: float, regime_maturity: float) -> str:
        """Determine expected regime evolution"""
        
        if transition_probability > 0.7:
            return "regime_change_likely"
        elif transition_probability > 0.4:
            return "regime_change_possible"
        elif regime_maturity > 0.8:
            return "regime_aging"
        else:
            return "regime_stable"
    
    def _calculate_max_drawdown(self, prices: np.ndarray) -> float:
        """Calculate maximum drawdown over the period"""
        
        if len(prices) < 2:
            return 0.0
        
        peak = prices[0]
        max_dd = 0.0
        
        for price in prices[1:]:
            if price > peak:
                peak = price
            else:
                drawdown = (peak - price) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    async def _update_timeframe_buffers(self, symbol: str, price: float):
        """Update multi-timeframe data buffers"""
        
        # Initialize symbol buffers if needed
        for timeframe in self.timeframe_buffers:
            if symbol not in self.timeframe_buffers[timeframe]:
                self.timeframe_buffers[timeframe][symbol] = []
        
        # Increment counters for each timeframe
        for timeframe in self.timeframe_counters:
            self.timeframe_counters[timeframe] += 1
            
            # Check if it's time to aggregate for this timeframe
            if self.timeframe_counters[timeframe] >= self.timeframe_intervals[timeframe]:
                # Aggregate data for this timeframe
                await self._aggregate_timeframe_data(symbol, price, timeframe)
                # Reset counter
                self.timeframe_counters[timeframe] = 0
    
    async def _aggregate_timeframe_data(self, symbol: str, price: float, timeframe: str):
        """Aggregate data for a specific timeframe"""
        
        # For now, we'll use the latest price as the aggregated value
        # In a full implementation, you'd aggregate OHLCV data properly
        self.timeframe_buffers[timeframe][symbol].append(price)
        
        # Keep only recent data for each timeframe
        max_points = {
            "5min": 288,    # 1 day of 5-minute bars
            "1H": 168,      # 1 week of hourly bars
            "1D": 252,      # 1 year of daily bars
            "1W": 104       # 2 years of weekly bars
        }
        
        if len(self.timeframe_buffers[timeframe][symbol]) > max_points[timeframe]:
            self.timeframe_buffers[timeframe][symbol] = \
                self.timeframe_buffers[timeframe][symbol][-max_points[timeframe]:]
    
    async def _analyze_multi_timeframe_regimes(self) -> Dict[str, TimeframeRegime]:
        """Analyze regimes across multiple timeframes"""
        
        timeframe_regimes = {}
        
        for timeframe in ["5min", "1H", "1D", "1W"]:
            try:
                regime_analysis = await self._analyze_timeframe_regime(timeframe)
                if regime_analysis:
                    timeframe_regimes[timeframe] = regime_analysis
            except Exception as e:
                logger.debug(f"Failed to analyze {timeframe} regime: {e}")
        
        return timeframe_regimes
    
    async def _analyze_timeframe_regime(self, timeframe: str) -> Optional[TimeframeRegime]:
        """Analyze regime for a specific timeframe"""
        
        # Get aggregated price data for this timeframe
        timeframe_data = self._get_timeframe_data(timeframe)
        
        if not timeframe_data or len(timeframe_data) < 20:
            return None
        
        # Calculate timeframe-specific metrics
        prices = np.array(timeframe_data)
        
        # Volatility calculation
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        
        # Trend strength calculation
        if len(prices) >= 20:
            short_ma = np.mean(prices[-10:])
            long_ma = np.mean(prices[-20:])
            trend_strength = abs(short_ma - long_ma) / long_ma if long_ma != 0 else 0
        else:
            trend_strength = 0
        
        # Determine regime for this timeframe
        regime, confidence = self._classify_timeframe_regime(volatility, trend_strength, returns)
        
        # Calculate transition probability
        transition_prob = self._calculate_timeframe_transition_probability(
            volatility, trend_strength, timeframe
        )
        
        return TimeframeRegime(
            timeframe=timeframe,
            regime=regime,
            confidence=confidence,
            trend_strength=trend_strength,
            volatility=volatility,
            regime_duration=1,  # Simplified for now
            transition_probability=transition_prob
        )
    
    def _get_timeframe_data(self, timeframe: str) -> List[float]:
        """Get aggregated data for a timeframe across all symbols"""
        
        all_data = []
        
        for symbol, prices in self.timeframe_buffers[timeframe].items():
            if prices:
                all_data.extend(prices)
        
        return all_data
    
    def _classify_timeframe_regime(self, volatility: float, trend_strength: float, 
                                 returns: np.ndarray) -> tuple[MarketRegime, float]:
        """Classify regime for a specific timeframe"""
        
        # Simplified regime classification
        if volatility > 0.25:
            if trend_strength > 0.02:
                regime = MarketRegime.BULL_HIGH_VOL if np.mean(returns) > 0 else MarketRegime.BEAR_HIGH_VOL
            else:
                regime = MarketRegime.CHOPPY
        elif volatility < 0.08:
            if trend_strength > 0.01:
                regime = MarketRegime.BULL_LOW_VOL if np.mean(returns) > 0 else MarketRegime.BEAR_LOW_VOL
            else:
                regime = MarketRegime.COMPLACENCY_MODE
        else:
            if trend_strength > 0.015:
                regime = MarketRegime.STRONG_TRENDING
            else:
                regime = MarketRegime.RANGE_BOUND
        
        # Calculate confidence based on clarity of signals
        confidence = min(0.95, 0.5 + abs(trend_strength) * 10 + abs(volatility - 0.15) * 2)
        
        return regime, confidence
    
    def _calculate_timeframe_transition_probability(self, volatility: float, 
                                                  trend_strength: float, 
                                                  timeframe: str) -> float:
        """Calculate transition probability for a timeframe"""
        
        # Base transition probability varies by timeframe
        base_prob = {
            "5min": 0.4,    # High frequency changes
            "1H": 0.3,      # Moderate changes
            "1D": 0.2,      # Slower changes
            "1W": 0.1       # Very slow changes
        }.get(timeframe, 0.2)
        
        # Adjust based on volatility and trend strength
        vol_adjustment = min(0.3, volatility * 1.5)
        trend_adjustment = min(0.2, trend_strength * 10)
        
        transition_prob = base_prob + vol_adjustment + trend_adjustment
        
        return np.clip(transition_prob, 0.0, 1.0)
    
    def _calculate_regime_consensus(self, timeframe_regimes: Dict[str, TimeframeRegime]) -> float:
        """Calculate consensus across timeframes"""
        
        if not timeframe_regimes or len(timeframe_regimes) < 2:
            return 0.5
        
        # Get regime types
        regimes = [tr.regime for tr in timeframe_regimes.values()]
        
        # Calculate agreement
        regime_counts = {}
        for regime in regimes:
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        # Most common regime
        max_count = max(regime_counts.values())
        consensus = max_count / len(regimes)
        
        return consensus
    
    def _determine_dominant_timeframe(self, timeframe_regimes: Dict[str, TimeframeRegime]) -> str:
        """Determine the most influential timeframe"""
        
        if not timeframe_regimes:
            return "1D"
        
        # Weight by confidence and hierarchy
        weighted_scores = {}
        
        for timeframe, regime_data in timeframe_regimes.items():
            hierarchy_weight = self.current_regime.regime_hierarchy.get(timeframe, 0.25) if self.current_regime else 0.25
            confidence_weight = regime_data.confidence
            
            weighted_scores[timeframe] = hierarchy_weight * confidence_weight
        
        # Return timeframe with highest weighted score
        return max(weighted_scores.items(), key=lambda x: x[1])[0]
    
    async def _predict_regime_transitions(self, current_analysis: RegimeAnalysis) -> Dict[str, TransitionPrediction]:
        """Generate ML-based regime transition predictions"""
        
        predictions = {}
        
        # Extract features for ML prediction
        features = self._extract_transition_features(current_analysis)
        
        if features is None or not self.models_trained:
            # Use fallback statistical prediction
            return self._generate_statistical_predictions(current_analysis)
        
        # Generate predictions for each time horizon
        for horizon in ["1H", "1D", "1W"]:
            try:
                prediction = await self._predict_transition_for_horizon(
                    features, current_analysis, horizon
                )
                if prediction:
                    predictions[horizon] = prediction
            except Exception as e:
                logger.debug(f"Failed to predict transition for {horizon}: {e}")
        
        return predictions
    
    def _extract_transition_features(self, analysis: RegimeAnalysis) -> Optional[np.ndarray]:
        """Extract features for ML transition prediction"""
        
        try:
            features = []
            
            # Basic regime features
            features.extend([
                analysis.confidence,
                analysis.trend_strength,
                analysis.stress_level,
                analysis.regime_stability,
                analysis.transition_probability,
                analysis.regime_maturity,
                analysis.regime_consensus
            ])
            
            # Volatility features
            if hasattr(analysis, 'volatility_regime'):
                vol_encoding = {
                    'low': 0.2, 'normal': 0.5, 'high': 0.8, 'extreme': 1.0
                }.get(analysis.volatility_regime, 0.5)
                features.append(vol_encoding)
            else:
                features.append(0.5)
            
            # Directional features
            if hasattr(analysis, 'directional_regime'):
                dir_encoding = {
                    'bear': -1.0, 'sideways': 0.0, 'bull': 1.0
                }.get(analysis.directional_regime, 0.0)
                features.append(dir_encoding)
            else:
                features.append(0.0)
            
            # Multi-timeframe features
            if analysis.timeframe_regimes:
                # Count of active timeframes
                features.append(len(analysis.timeframe_regimes))
                
                # Average confidence across timeframes
                avg_confidence = np.mean([
                    tf.confidence for tf in analysis.timeframe_regimes.values()
                ])
                features.append(avg_confidence)
                
                # Average volatility across timeframes
                avg_volatility = np.mean([
                    tf.volatility for tf in analysis.timeframe_regimes.values()
                ])
                features.append(avg_volatility)
                
                # Average transition probability across timeframes
                avg_transition = np.mean([
                    tf.transition_probability for tf in analysis.timeframe_regimes.values()
                ])
                features.append(avg_transition)
            else:
                features.extend([0, 0.5, 0.1, 0.2])  # Default values
            
            # Risk adjustment features
            features.extend([
                analysis.risk_adjustment,
                analysis.position_sizing_factor
            ])
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.debug(f"Failed to extract transition features: {e}")
            return None
    
    async def _predict_transition_for_horizon(self, features: np.ndarray, 
                                            current_analysis: RegimeAnalysis, 
                                            horizon: str) -> Optional[TransitionPrediction]:
        """Predict regime transition for specific time horizon"""
        
        try:
            model = self.transition_models[horizon]
            
            # Scale features
            scaled_features = self.transition_scaler.transform(features)
            
            # Get prediction probabilities
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(scaled_features)[0]
                predicted_class = model.predict(scaled_features)[0]
                confidence = np.max(probabilities)
            else:
                predicted_class = model.predict(scaled_features)[0]
                confidence = 0.7  # Default confidence for models without probability
            
            # Map prediction to regime
            predicted_regime = self._map_prediction_to_regime(predicted_class, current_analysis)
            
            # Calculate transition probability
            current_regime_idx = self._get_regime_index(current_analysis.primary_regime)
            if current_regime_idx != predicted_class:
                transition_prob = confidence
            else:
                transition_prob = 1.0 - confidence
            
            # Identify contributing factors
            contributing_factors = self._identify_contributing_factors(
                features, current_analysis, horizon
            )
            
            # Get model accuracy (simplified)
            model_accuracy = getattr(model, 'score_', 0.75)  # Default if not available
            
            return TransitionPrediction(
                current_regime=current_analysis.primary_regime,
                predicted_regime=predicted_regime,
                transition_probability=transition_prob,
                confidence=confidence,
                time_horizon=horizon,
                contributing_factors=contributing_factors,
                model_accuracy=model_accuracy,
                prediction_timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.debug(f"Failed to predict transition for {horizon}: {e}")
            return None
    
    def _generate_statistical_predictions(self, analysis: RegimeAnalysis) -> Dict[str, TransitionPrediction]:
        """Generate statistical-based predictions when ML models not available"""
        
        predictions = {}
        
        # Simple statistical predictions based on current analysis
        base_transition_prob = analysis.transition_probability
        
        for horizon in ["1H", "1D", "1W"]:
            # Adjust probability by time horizon
            horizon_multiplier = {"1H": 1.5, "1D": 1.0, "1W": 0.7}[horizon]
            adjusted_prob = min(0.95, base_transition_prob * horizon_multiplier)
            
            # Predict most likely next regime (simplified)
            predicted_regime = self._predict_next_regime_statistical(analysis)
            
            predictions[horizon] = TransitionPrediction(
                current_regime=analysis.primary_regime,
                predicted_regime=predicted_regime,
                transition_probability=adjusted_prob,
                confidence=0.6,  # Lower confidence for statistical method
                time_horizon=horizon,
                contributing_factors=["statistical_analysis", "regime_maturity"],
                model_accuracy=0.65,  # Estimated accuracy
                prediction_timestamp=datetime.now()
            )
        
        return predictions
    
    def _map_prediction_to_regime(self, prediction_class: int, 
                                current_analysis: RegimeAnalysis) -> MarketRegime:
        """Map ML prediction class to MarketRegime"""
        
        # Simplified mapping - in production, this would be more sophisticated
        regime_mapping = {
            0: MarketRegime.COMPLACENCY_MODE,
            1: MarketRegime.BULL_LOW_VOL,
            2: MarketRegime.BEAR_LOW_VOL,
            3: MarketRegime.RANGE_BOUND,
            4: MarketRegime.CHOPPY,
            5: MarketRegime.BULL_HIGH_VOL,
            6: MarketRegime.BEAR_HIGH_VOL,
            7: MarketRegime.CRISIS_MODE
        }
        
        return regime_mapping.get(prediction_class, current_analysis.primary_regime)
    
    def _get_regime_index(self, regime: MarketRegime) -> int:
        """Get numeric index for regime (for ML training)"""
        
        regime_indices = {
            MarketRegime.COMPLACENCY_MODE: 0,
            MarketRegime.BULL_LOW_VOL: 1,
            MarketRegime.BEAR_LOW_VOL: 2,
            MarketRegime.RANGE_BOUND: 3,
            MarketRegime.CHOPPY: 4,
            MarketRegime.BULL_HIGH_VOL: 5,
            MarketRegime.BEAR_HIGH_VOL: 6,
            MarketRegime.CRISIS_MODE: 7
        }
        
        return regime_indices.get(regime, 0)
    
    def _predict_next_regime_statistical(self, analysis: RegimeAnalysis) -> MarketRegime:
        """Predict next regime using statistical methods"""
        
        current = analysis.primary_regime
        
        # Simple transition logic based on current regime characteristics
        if analysis.stress_level > 0.7:
            return MarketRegime.CRISIS_MODE
        elif analysis.volatility_regime == "high" and analysis.trend_strength > 0.02:
            if analysis.directional_regime == "bull":
                return MarketRegime.BULL_HIGH_VOL
            else:
                return MarketRegime.BEAR_HIGH_VOL
        elif analysis.volatility_regime == "low" and analysis.trend_strength < 0.01:
            return MarketRegime.RANGE_BOUND
        else:
            # Default to current regime if no clear transition signal
            return current
    
    def _identify_contributing_factors(self, features: np.ndarray, 
                                     analysis: RegimeAnalysis, 
                                     horizon: str) -> List[str]:
        """Identify key factors contributing to transition prediction"""
        
        factors = []
        
        # Analyze feature importance (simplified)
        if analysis.stress_level > 0.5:
            factors.append("elevated_stress_level")
        
        if analysis.transition_probability > 0.6:
            factors.append("high_base_transition_probability")
        
        if analysis.regime_consensus < 0.5:
            factors.append("weak_timeframe_consensus")
        
        if analysis.regime_maturity > 0.8:
            factors.append("mature_regime")
        
        if len(analysis.timeframe_regimes or {}) > 2:
            factors.append("multi_timeframe_signals")
        
        return factors if factors else ["normal_market_conditions"]
    
    async def _train_transition_models(self):
        """Train ML models on historical transition data"""
        
        if len(self.transition_history) < 50:  # Need minimum data
            logger.debug("Insufficient data for ML model training")
            return
        
        try:
            # Prepare training data
            X, y = self._prepare_training_data()
            
            if X is None or len(X) < 20:
                logger.debug("Insufficient training features")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.transition_scaler.fit_transform(X_train)
            X_test_scaled = self.transition_scaler.transform(X_test)
            
            # Train models for each horizon
            for horizon, model in self.transition_models.items():
                try:
                    # Train model
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluate model
                    y_pred = model.predict(X_test_scaled)
                    accuracy = accuracy_score(y_test, y_pred)
                    
                    # Store accuracy
                    model.score_ = accuracy
                    
                    logger.info(f"✅ Trained {horizon} transition model: {accuracy:.3f} accuracy")
                    
                except Exception as e:
                    logger.debug(f"Failed to train {horizon} model: {e}")
            
            self.models_trained = True
            logger.info("🎯 ML transition models training completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to train transition models: {e}")
    
    def _prepare_training_data(self) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Prepare training data from historical transitions"""
        
        if not self.feature_history or not self.transition_history:
            return None, None
        
        try:
            # Convert feature history to numpy array
            X = np.array(self.feature_history)
            
            # Convert transition history to labels
            y = np.array([
                self._get_regime_index(transition.predicted_regime) 
                for transition in self.transition_history
            ])
            
            return X, y
            
        except Exception as e:
            logger.debug(f"Failed to prepare training data: {e}")
            return None, None
    
    def _calculate_ml_transition_probability(self, predictions: Dict[str, TransitionPrediction]) -> float:
        """Calculate weighted ML transition probability across horizons"""
        
        if not predictions:
            return 0.0
        
        # Weight predictions by time horizon importance
        horizon_weights = {"1H": 0.3, "1D": 0.5, "1W": 0.2}
        
        weighted_prob = 0.0
        total_weight = 0.0
        
        for horizon, prediction in predictions.items():
            weight = horizon_weights.get(horizon, 0.33)
            weighted_prob += prediction.transition_probability * weight
            total_weight += weight
        
        return weighted_prob / total_weight if total_weight > 0 else 0.0
    
    def _calculate_transition_confidence(self, predictions: Dict[str, TransitionPrediction]) -> float:
        """Calculate overall confidence in transition predictions"""
        
        if not predictions:
            return 0.0
        
        # Average confidence across all predictions
        confidences = [pred.confidence for pred in predictions.values()]
        return np.mean(confidences)
    
    def _determine_most_likely_next_regime(self, predictions: Dict[str, TransitionPrediction]) -> Optional[MarketRegime]:
        """Determine the most likely next regime from ML predictions"""
        
        if not predictions:
            return None
        
        # Count regime predictions weighted by confidence
        regime_scores = {}
        
        for prediction in predictions.values():
            regime = prediction.predicted_regime
            score = prediction.confidence * prediction.transition_probability
            
            if regime not in regime_scores:
                regime_scores[regime] = 0
            regime_scores[regime] += score
        
        # Return regime with highest weighted score
        if regime_scores:
            return max(regime_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _determine_enhanced_regime(self, volatility: float, trend_strength: float) -> tuple[str, float]:
        """
        Determine regime with enhanced logic from test implementation
        Returns: (regime_name, risk_multiplier)
        """
        if volatility > 0.03:  # High volatility
            if abs(trend_strength) > 0.02:
                regime = 'volatile_trending'
                risk_multiplier = 1.5
            else:
                regime = 'volatile_ranging'
                risk_multiplier = 1.8
        else:  # Low volatility
            if abs(trend_strength) > 0.01:
                regime = 'calm_trending'
                risk_multiplier = 0.8
            else:
                regime = 'calm_ranging'
                risk_multiplier = 0.6
        
        return regime, risk_multiplier
    
    def _map_enhanced_regime_to_enum(self, regime: str) -> MarketRegime:
        """Map enhanced regime strings to MarketRegime enum"""
        regime_mapping = {
            'volatile_trending': MarketRegime.HIGH_VOLATILITY,
            'volatile_ranging': MarketRegime.HIGH_VOLATILITY,
            'calm_trending': MarketRegime.TRENDING,
            'calm_ranging': MarketRegime.MEAN_REVERTING
        }
        return regime_mapping.get(regime, MarketRegime.SIDEWAYS)
    
    def _calculate_enhanced_strategy_suitability(self, regime: str, volatility: float, trend_strength: float) -> Dict[str, float]:
        """
        Calculate enhanced strategy suitability
        ENHANCED: From test implementation with regime-specific weights
        """
        # Base suitability
        suitability = {
            'momentum': 0.5,
            'mean_reversion': 0.5,
            'pairs_trading': 0.5
        }
        
        # Enhanced regime-specific adjustments
        if regime in ['volatile_trending', 'calm_trending']:
            # Trending markets favor momentum
            suitability['momentum'] = 0.7 + min(0.2, abs(trend_strength) * 10)
            suitability['mean_reversion'] = 0.3 - min(0.1, abs(trend_strength) * 5)
            suitability['pairs_trading'] = 0.6
        elif regime in ['volatile_ranging', 'calm_ranging']:
            # Ranging markets favor mean reversion
            suitability['momentum'] = 0.3 - min(0.1, volatility * 5)
            suitability['mean_reversion'] = 0.7 + min(0.2, volatility * 3)
            suitability['pairs_trading'] = 0.8
        
        # Volatility adjustments
        if volatility > 0.03:  # High volatility
            suitability['momentum'] *= 1.1  # Slightly favor momentum in volatile markets
            suitability['pairs_trading'] *= 0.8  # Reduce pairs trading in high volatility
        
        # Ensure values are in valid range [0, 1]
        for strategy in suitability:
            suitability[strategy] = max(0.1, min(1.0, suitability[strategy]))
        
        return suitability
    
    def _perform_basic_regime_analysis(self, prices: np.ndarray) -> RegimeAnalysis:
        """Fallback basic regime analysis"""
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)
        trend_strength = self._calculate_trend_strength(prices)
        primary_regime = self._classify_regime(returns, volatility, trend_strength)
        strategy_suitability = self._calculate_strategy_suitability(primary_regime, volatility, trend_strength)
        confidence = min(0.95, max(0.5, abs(trend_strength) + (1 - volatility)))
        
        return RegimeAnalysis(
            primary_regime=primary_regime,
            confidence=confidence,
            volatility_regime="high_volatility" if volatility > 0.25 else "low_volatility",
            trend_strength=trend_strength,
            regime_duration=self._calculate_regime_duration(),
            strategy_suitability=strategy_suitability,
            timestamp=datetime.now()
        )
    
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

    async def detect_transition(
        self,
        old_regime: str,
        new_regime: str,
        transition_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect and analyze regime transitions
        
        This method analyzes whether a regime transition has occurred
        and provides details about the transition characteristics.
        """
        try:
            # Get current regime analysis
            current_analysis = await self.analyze_regime()
            
            if not current_analysis:
                return {
                    'transition_detected': False,
                    'confidence': 0.0,
                    'error': 'No regime analysis available'
                }
            
            # Check if transition matches the requested regimes
            current_regime_str = current_analysis.primary_regime.value
            
            # If we have historical regime data, compare
            if self.regime_history:
                previous_regime = self.regime_history[-1].primary_regime.value
                
                # Check if this matches the requested transition
                transition_detected = (
                    previous_regime == old_regime and 
                    current_regime_str == new_regime
                )
                
                if transition_detected:
                    # Calculate transition characteristics
                    transition_confidence = min(
                        current_analysis.confidence,
                        self.regime_history[-1].confidence
                    )
                    
                    # Calculate transition magnitude
                    old_stress = self.regime_history[-1].stress_level
                    new_stress = current_analysis.stress_level
                    transition_magnitude = abs(new_stress - old_stress)
                    
                    return {
                        'transition_detected': True,
                        'confidence': transition_confidence,
                        'magnitude': transition_magnitude,
                        'old_regime': old_regime,
                        'new_regime': new_regime,
                        'transition_probability': current_analysis.transition_probability,
                        'regime_stability': current_analysis.regime_stability
                    }
            
            # No transition detected or insufficient history
            return {
                'transition_detected': False,
                'confidence': current_analysis.confidence,
                'current_regime': current_regime_str,
                'transition_probability': current_analysis.transition_probability
            }
            
        except Exception as e:
            logger.error(f"Error detecting regime transition: {e}")
            return {
                'transition_detected': False,
                'confidence': 0.0,
                'error': str(e)
            }

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