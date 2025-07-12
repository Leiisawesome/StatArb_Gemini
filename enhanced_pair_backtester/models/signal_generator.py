"""
Signal Generation Module for Enhanced Pair Backtesting System

This module integrates all our models (spread calculation, Kalman filter, HMM regime detection, 
and ensemble filter) to generate comprehensive trading signals with regime-aware thresholds.

Author: Enhanced Pair Backtesting System
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

try:
    from ..utils.spread_calculator import SpreadCalculator
    from .kalman_filter import KalmanHedgeRatioFilter, create_kalman_filter
    from .hmm_regime_optimized import OptimizedHMMRegimeDetector, create_optimized_hmm_detector
    from .ensemble_filter_simple import SimpleEnsembleFilter, create_simple_ensemble_filter
except ImportError:
    # Fallback for direct module execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils.spread_calculator import SpreadCalculator
    from models.kalman_filter import KalmanHedgeRatioFilter, create_kalman_filter
    from models.hmm_regime_optimized import OptimizedHMMRegimeDetector, create_optimized_hmm_detector
    from models.ensemble_filter_simple import SimpleEnsembleFilter, create_simple_ensemble_filter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Trading signal types"""
    LONG = 1
    SHORT = -1
    HOLD = 0

class RegimeType(Enum):
    """Market regime types"""
    MEAN_REVERTING = 0
    TRENDING = 1
    VOLATILE = 2

@dataclass
class SignalConfig:
    """Configuration for signal generation"""
    # Z-score thresholds by regime
    mean_reverting_entry: float = 2.0
    mean_reverting_exit: float = 0.5
    trending_entry: float = 1.5
    trending_exit: float = 0.3
    volatile_entry: float = 3.0
    volatile_exit: float = 1.0
    
    # Ensemble filter settings
    ensemble_confidence_threshold: float = 0.7
    ensemble_strength_threshold: float = 60.0
    
    # Position sizing parameters
    max_position_size: float = 0.3  # 30% max position
    min_position_size: float = 0.05  # 5% min position
    kelly_fraction: float = 0.25  # Kelly fraction multiplier
    
    # Risk management
    max_drawdown_threshold: float = 0.15  # 15% max drawdown
    volatility_scaling: bool = True
    regime_switching_penalty: float = 0.1  # Reduce position size during regime switches
    
    # Signal quality filters
    min_cointegration_score: float = 0.05  # Minimum p-value for cointegration
    min_correlation: float = 0.5  # Minimum correlation
    max_hedge_ratio_volatility: float = 0.5  # Maximum hedge ratio volatility

@dataclass
class TradingSignal:
    """Complete trading signal with all metadata"""
    timestamp: datetime
    signal_type: SignalType
    strength: float  # 0-100
    confidence: float  # 0-1
    position_size: float  # 0-1
    entry_price: float
    stop_loss: float
    take_profit: float
    regime: RegimeType
    z_score: float
    hedge_ratio: float
    spread_value: float
    ensemble_prediction: Optional[int] = None
    ensemble_confidence: Optional[float] = None
    quality_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

class SignalGenerator:
    """
    Comprehensive signal generator that integrates all models
    """
    
    def __init__(self, config: Optional[SignalConfig] = None):
        self.config = config or SignalConfig()
        self.spread_calculator: Optional[SpreadCalculator] = None
        self.kalman_filter: Optional[KalmanHedgeRatioFilter] = None
        self.hmm_detector: Optional[OptimizedHMMRegimeDetector] = None
        self.ensemble_filter: Optional[SimpleEnsembleFilter] = None
        
        # State tracking
        self.current_position = 0.0
        self.current_regime = None
        self.regime_change_count = 0
        self.last_regime_change = None
        
        # Performance tracking
        self.signal_history = []
        self.performance_metrics = {}
        
        logger.info("Signal Generator initialized")
    
    def initialize_models(self, data: pd.DataFrame, symbols: List[str]) -> bool:
        """Initialize all models with data"""
        try:
            logger.info("Initializing signal generation models...")
            
            # Initialize spread calculator
            config = {'hedge_ratio_method': 'kalman', 'lookback_window': 60}
            self.spread_calculator = SpreadCalculator(config)
            
            # Extract price series based on data structure
            if f'{symbols[0]}_close' in data.columns:
                price1 = data[f'{symbols[0]}_close']
                price2 = data[f'{symbols[1]}_close']
            elif symbols[0] in data.columns:
                price1 = data[symbols[0]]
                price2 = data[symbols[1]]
            else:
                logger.error(f"Could not find price data for {symbols[0]} and {symbols[1]}")
                return False
            
            spread_results = self.spread_calculator.calculate_spread(
                price1, price2, symbols[0], symbols[1]
            )
            
            if spread_results is None:
                logger.error("Failed to calculate spread")
                return False
            
            # Initialize Kalman filter
            self.kalman_filter = KalmanHedgeRatioFilter(auto_tune=True)
            kalman_results = self.kalman_filter.fit(
                price2.values, price1.values
            )
            
            # Initialize HMM regime detector
            self.hmm_detector = OptimizedHMMRegimeDetector(n_states=3)
            hmm_results = self.hmm_detector.fit(spread_results.spread)
            
            # Initialize ensemble filter
            self.ensemble_filter = SimpleEnsembleFilter()
            ensemble_results = self.ensemble_filter.fit(spread_results.spread, hmm_results)
            
            logger.info("All models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing models: {e}")
            return False
    
    def generate_signals(self, data: pd.DataFrame, symbols: List[str]) -> List[TradingSignal]:
        """
        Generate comprehensive trading signals for the entire dataset
        """
        try:
            logger.info(f"Generating signals for {len(data)} data points...")
            
            # Initialize models
            if not self.initialize_models(data, symbols):
                return []
            
            # Get all model outputs
            spread_results = self.spread_calculator.calculate_spread(
                data, symbols[0], symbols[1], method='kalman'
            )
            
            kalman_results = self.kalman_filter.fit_and_predict(
                data[symbols[1]].values, data[symbols[0]].values
            )
            
            hmm_results = self.hmm_detector.fit_predict(spread_results['spread'].values)
            
            ensemble_results = self.ensemble_filter.train_and_predict(
                data, spread_results, hmm_results, symbols
            )
            
            # Generate signals for each time point
            signals = []
            for i in range(len(data)):
                signal = self._generate_single_signal(
                    data.iloc[i], spread_results, kalman_results, 
                    hmm_results, ensemble_results, i
                )
                if signal:
                    signals.append(signal)
            
            self.signal_history.extend(signals)
            logger.info(f"Generated {len(signals)} trading signals")
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return []
    
    def _generate_single_signal(self, data_point: pd.Series, spread_results: Dict,
                              kalman_results: Dict, hmm_results: Dict,
                              ensemble_results: Dict, index: int) -> Optional[TradingSignal]:
        """Generate a single trading signal for a specific time point"""
        try:
            # Extract current values
            timestamp = data_point.name if hasattr(data_point, 'name') else datetime.now()
            current_spread = spread_results['spread'].iloc[index]
            current_z_score = spread_results['z_score'].iloc[index]
            current_hedge_ratio = kalman_results['hedge_ratios'][index]
            current_regime = hmm_results['states'][index]
            
            # Skip if we have NaN values
            if np.isnan(current_spread) or np.isnan(current_z_score):
                return None
            
            # Determine regime type
            regime_type = self._classify_regime(current_regime, hmm_results)
            
            # Get regime-specific thresholds
            entry_threshold, exit_threshold = self._get_regime_thresholds(regime_type)
            
            # Determine base signal
            signal_type = self._determine_signal_type(
                current_z_score, entry_threshold, exit_threshold
            )
            
            # Calculate signal strength
            strength = self._calculate_signal_strength(
                current_z_score, entry_threshold, regime_type
            )
            
            # Apply ensemble filter
            ensemble_prediction = ensemble_results.get('prediction', 0)
            ensemble_confidence = ensemble_results.get('confidence', 0.5)
            
            # Apply ensemble filtering
            if ensemble_confidence < self.config.ensemble_confidence_threshold:
                signal_type = SignalType.HOLD
                strength *= 0.5  # Reduce strength for low confidence
            
            if strength < self.config.ensemble_strength_threshold:
                signal_type = SignalType.HOLD
            
            # Calculate position size
            position_size = self._calculate_position_size(
                strength, current_z_score, regime_type, ensemble_confidence
            )
            
            # Calculate stop loss and take profit
            stop_loss, take_profit = self._calculate_risk_levels(
                data_point, current_spread, signal_type, regime_type
            )
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                spread_results, kalman_results, hmm_results, index
            )
            
            # Create signal
            signal = TradingSignal(
                timestamp=timestamp,
                signal_type=signal_type,
                strength=strength,
                confidence=ensemble_confidence,
                position_size=position_size,
                entry_price=current_spread,
                stop_loss=stop_loss,
                take_profit=take_profit,
                regime=regime_type,
                z_score=current_z_score,
                hedge_ratio=current_hedge_ratio,
                spread_value=current_spread,
                ensemble_prediction=ensemble_prediction,
                ensemble_confidence=ensemble_confidence,
                quality_score=quality_score,
                metadata={
                    'entry_threshold': entry_threshold,
                    'exit_threshold': exit_threshold,
                    'regime_index': current_regime,
                    'data_index': index
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating single signal at index {index}: {e}")
            return None
    
    def _classify_regime(self, regime_index: int, hmm_results: Dict) -> RegimeType:
        """Classify regime based on HMM results"""
        # Get regime characteristics
        means = hmm_results.get('means', [0, 0, 0])
        covariances = hmm_results.get('covariances', [1, 1, 1])
        
        # Sort regimes by volatility
        regime_volatilities = [(i, np.sqrt(covariances[i])) for i in range(len(covariances))]
        regime_volatilities.sort(key=lambda x: x[1])
        
        # Classify based on volatility ranking
        if regime_index == regime_volatilities[0][0]:  # Lowest volatility
            return RegimeType.MEAN_REVERTING
        elif regime_index == regime_volatilities[1][0]:  # Medium volatility
            return RegimeType.TRENDING
        else:  # Highest volatility
            return RegimeType.VOLATILE
    
    def _get_regime_thresholds(self, regime_type: RegimeType) -> Tuple[float, float]:
        """Get entry and exit thresholds for specific regime"""
        if regime_type == RegimeType.MEAN_REVERTING:
            return self.config.mean_reverting_entry, self.config.mean_reverting_exit
        elif regime_type == RegimeType.TRENDING:
            return self.config.trending_entry, self.config.trending_exit
        else:  # VOLATILE
            return self.config.volatile_entry, self.config.volatile_exit
    
    def _determine_signal_type(self, z_score: float, entry_threshold: float, 
                             exit_threshold: float) -> SignalType:
        """Determine signal type based on z-score and thresholds"""
        if abs(z_score) < exit_threshold:
            return SignalType.HOLD
        elif z_score > entry_threshold:
            return SignalType.SHORT  # Spread is too high, short it
        elif z_score < -entry_threshold:
            return SignalType.LONG   # Spread is too low, long it
        else:
            return SignalType.HOLD
    
    def _calculate_signal_strength(self, z_score: float, entry_threshold: float,
                                 regime_type: RegimeType) -> float:
        """Calculate signal strength (0-100)"""
        # Base strength from z-score magnitude
        base_strength = min(abs(z_score) / entry_threshold * 50, 100)
        
        # Regime-specific adjustments
        if regime_type == RegimeType.MEAN_REVERTING:
            base_strength *= 1.2  # Boost mean-reverting signals
        elif regime_type == RegimeType.VOLATILE:
            base_strength *= 0.8  # Reduce volatile regime signals
        
        return max(0, min(100, base_strength))
    
    def _calculate_position_size(self, strength: float, z_score: float,
                               regime_type: RegimeType, ensemble_confidence: float) -> float:
        """Calculate position size based on multiple factors"""
        # Base position size from strength
        base_size = (strength / 100) * self.config.max_position_size
        
        # Kelly criterion adjustment
        kelly_adjustment = abs(z_score) * self.config.kelly_fraction
        base_size *= (1 + kelly_adjustment)
        
        # Ensemble confidence adjustment
        base_size *= ensemble_confidence
        
        # Regime-specific adjustments
        if regime_type == RegimeType.VOLATILE:
            base_size *= 0.5  # Reduce size in volatile regimes
        elif regime_type == RegimeType.MEAN_REVERTING:
            base_size *= 1.1  # Slightly increase for mean-reverting
        
        # Apply regime switching penalty
        if self.last_regime_change and regime_type != self.current_regime:
            base_size *= (1 - self.config.regime_switching_penalty)
            self.regime_change_count += 1
            self.last_regime_change = datetime.now()
        
        # Ensure within bounds
        return max(self.config.min_position_size, 
                  min(self.config.max_position_size, base_size))
    
    def _calculate_risk_levels(self, data_point: pd.Series, entry_price: float,
                             signal_type: SignalType, regime_type: RegimeType) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        # Estimate volatility from recent data (simplified)
        volatility = 0.02  # Default 2% volatility
        
        # Regime-specific risk adjustments
        if regime_type == RegimeType.VOLATILE:
            volatility *= 2.0
        elif regime_type == RegimeType.MEAN_REVERTING:
            volatility *= 0.8
        
        # Calculate stop loss (2x volatility)
        stop_distance = 2 * volatility
        
        # Calculate take profit (1.5x volatility for better risk/reward)
        profit_distance = 1.5 * volatility
        
        if signal_type == SignalType.LONG:
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + profit_distance
        elif signal_type == SignalType.SHORT:
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - profit_distance
        else:
            stop_loss = entry_price
            take_profit = entry_price
        
        return stop_loss, take_profit
    
    def _calculate_quality_score(self, spread_results: Dict, kalman_results: Dict,
                               hmm_results: Dict, index: int) -> float:
        """Calculate overall signal quality score"""
        try:
            # Spread quality (based on z-score stability)
            z_scores = spread_results['z_score']
            z_score_stability = 1.0 / (1.0 + np.std(z_scores.tail(20)))
            
            # Hedge ratio stability
            hedge_ratios = kalman_results['hedge_ratios']
            hedge_ratio_stability = 1.0 / (1.0 + np.std(hedge_ratios[-20:]))
            
            # Regime persistence
            states = hmm_results['states']
            recent_states = states[-20:] if len(states) >= 20 else states
            regime_persistence = len(set(recent_states)) / len(recent_states)
            regime_persistence = 1.0 - regime_persistence  # Invert (more persistent = higher score)
            
            # Combine scores
            quality_score = (z_score_stability * 0.4 + 
                           hedge_ratio_stability * 0.3 + 
                           regime_persistence * 0.3) * 100
            
            return max(0, min(100, quality_score))
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 50.0  # Default score
    
    def get_latest_signal(self, data: pd.DataFrame, symbols: List[str]) -> Optional[TradingSignal]:
        """Get the latest trading signal"""
        try:
            # Initialize models if not done
            if not self.spread_calculator:
                if not self.initialize_models(data, symbols):
                    return None
            
            # Get latest data point
            latest_data = data.iloc[-1]
            
            # Get model outputs for latest point
            spread_results = self.spread_calculator.calculate_spread(
                data, symbols[0], symbols[1], method='kalman'
            )
            
            kalman_results = self.kalman_filter.fit_and_predict(
                data[symbols[1]].values, data[symbols[0]].values
            )
            
            hmm_results = self.hmm_detector.fit_predict(spread_results['spread'].values)
            
            ensemble_results = self.ensemble_filter.train_and_predict(
                data, spread_results, hmm_results, symbols
            )
            
            # Generate signal for latest point
            signal = self._generate_single_signal(
                latest_data, spread_results, kalman_results,
                hmm_results, ensemble_results, len(data) - 1
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error getting latest signal: {e}")
            return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary of generated signals"""
        if not self.signal_history:
            return {}
        
        signals = self.signal_history
        
        # Basic statistics
        total_signals = len(signals)
        long_signals = len([s for s in signals if s.signal_type == SignalType.LONG])
        short_signals = len([s for s in signals if s.signal_type == SignalType.SHORT])
        hold_signals = len([s for s in signals if s.signal_type == SignalType.HOLD])
        
        # Quality metrics
        avg_strength = np.mean([s.strength for s in signals])
        avg_confidence = np.mean([s.confidence for s in signals])
        avg_quality = np.mean([s.quality_score for s in signals])
        
        # Regime distribution
        regime_counts = {}
        for signal in signals:
            regime = signal.regime.name
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        return {
            'total_signals': total_signals,
            'signal_distribution': {
                'long': long_signals,
                'short': short_signals,
                'hold': hold_signals
            },
            'average_metrics': {
                'strength': avg_strength,
                'confidence': avg_confidence,
                'quality_score': avg_quality
            },
            'regime_distribution': regime_counts,
            'regime_changes': self.regime_change_count
        } 