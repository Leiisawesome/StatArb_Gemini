"""
Regime-Aware Signal Filtering Module - Phase 2 Enhancement
Implements market regime detection and signal filtering based on market conditions
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Use canonical RegimeType from infrastructure
from ..infrastructure import MarketRegime as RegimeType

@dataclass
class RegimeConfig:
    """Configuration for regime-aware filtering"""
    # Regime detection settings
    lookback_period: int = 50
    volatility_threshold: float = 0.03  # 3% volatility threshold
    trend_strength_threshold: float = 0.6  # 60% trend strength threshold
    
    # Regime-specific filters
    regime_filters: Dict[str, Dict[str, Any]] = None
    
    # Market stress indicators
    stress_threshold: float = 0.7  # 70% stress threshold
    volume_threshold: float = 0.5  # 50% of average volume
    
    def __post_init__(self):
        if self.regime_filters is None:
            self.regime_filters = {
                'trending': {
                    'min_confidence': 0.6,
                    'max_volatility': 0.06,
                    'position_size_multiplier': 1.1,
                    'allowed_signals': ['LONG', 'SHORT']
                },
                'mean_reverting': {
                    'min_confidence': 0.7,
                    'max_volatility': 0.08,
                    'position_size_multiplier': 1.0,
                    'allowed_signals': ['LONG', 'SHORT']
                },
                'volatile': {
                    'min_confidence': 0.8,
                    'max_volatility': 0.15,
                    'position_size_multiplier': 0.7,
                    'allowed_signals': ['LONG', 'SHORT']
                },
                'stable': {
                    'min_confidence': 0.5,
                    'max_volatility': 0.04,
                    'position_size_multiplier': 1.05,
                    'allowed_signals': ['LONG', 'SHORT']
                },
                'unknown': {
                    'min_confidence': 0.8,
                    'max_volatility': 0.10,
                    'position_size_multiplier': 0.9,
                    'allowed_signals': ['LONG', 'SHORT']
                }
            }

class RegimeAwareFilter:
    """Filter signals based on current market regime"""
    
    def __init__(self, config: Optional[RegimeConfig] = None):
        self.config = config or RegimeConfig()
        self.regime_history = []
        self.filter_stats = {
            'signals_filtered': 0,
            'signals_accepted': 0,
            'regime_distribution': {}
        }
    
    def detect_market_regime(self, market_data: pd.DataFrame) -> Tuple[RegimeType, float]:
        """
        Detect current market regime based on price action and volatility
        
        Args:
            market_data: Historical market data
        
        Returns:
            Tuple of (regime_type, confidence)
        """
        try:
            if len(market_data) < self.config.lookback_period:
                return RegimeType.UNKNOWN, 0.5
            
            # Calculate volatility
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.std()
            
            # Calculate trend strength
            trend_strength = self._calculate_trend_strength(market_data)
            
            # Calculate mean reversion strength
            mean_reversion_strength = self._calculate_mean_reversion_strength(market_data)
            
            # Determine regime based on characteristics
            if volatility > self.config.volatility_threshold * 2:
                regime = RegimeType.VOLATILE
                confidence = min(0.9, volatility / 0.1)  # Higher volatility = higher confidence
            elif trend_strength > self.config.trend_strength_threshold:
                regime = RegimeType.TRENDING
                confidence = trend_strength
            elif mean_reversion_strength > 0.6:
                regime = RegimeType.MEAN_REVERTING
                confidence = mean_reversion_strength
            elif volatility < self.config.volatility_threshold * 0.5:
                regime = RegimeType.STABLE
                confidence = 1.0 - (volatility / self.config.volatility_threshold)
            else:
                regime = RegimeType.UNKNOWN
                confidence = 0.5
            
            # Store regime history
            self.regime_history.append({
                'regime': regime,
                'confidence': confidence,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'mean_reversion_strength': mean_reversion_strength
            })
            
            logger.debug(f"Regime detected: {regime.value}, confidence={confidence:.3f}, "
                        f"volatility={volatility:.3f}, trend_strength={trend_strength:.3f}")
            
            return regime, confidence
            
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return RegimeType.UNKNOWN, 0.5
    
    def filter_signals_by_regime(
        self,
        signals: List[Dict[str, Any]],
        regime: RegimeType,
        regime_confidence: float,
        market_data: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Filter signals based on current market regime
        
        Args:
            signals: List of trading signals
            regime: Current market regime
            regime_confidence: Regime detection confidence
            market_data: Historical market data
        
        Returns:
            Filtered list of signals
        """
        try:
            filtered_signals = []
            regime_config = self.config.regime_filters.get(regime.value, 
                                                         self.config.regime_filters['unknown'])
            
            # Calculate market stress indicator
            market_stress = self._calculate_market_stress(market_data)
            
            for signal in signals:
                if self._should_accept_signal(signal, regime, regime_confidence, 
                                            market_stress, regime_config):
                    # Adjust signal based on regime
                    adjusted_signal = self._adjust_signal_for_regime(signal, regime, 
                                                                   regime_confidence, regime_config)
                    filtered_signals.append(adjusted_signal)
                    self.filter_stats['signals_accepted'] += 1
                else:
                    self.filter_stats['signals_filtered'] += 1
            
            # Update regime distribution
            regime_name = regime.value
            self.filter_stats['regime_distribution'][regime_name] = (
                self.filter_stats['regime_distribution'].get(regime_name, 0) + 1
            )
            
            logger.debug(f"Signal filtering: {len(signals)} signals, "
                        f"{len(filtered_signals)} accepted, {self.filter_stats['signals_filtered']} filtered")
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Signal filtering failed: {e}")
            return signals  # Return original signals if filtering fails
    
    def _should_accept_signal(
        self,
        signal: Dict[str, Any],
        regime: RegimeType,
        regime_confidence: float,
        market_stress: float,
        regime_config: Dict[str, Any]
    ) -> bool:
        """Determine if signal should be accepted in current market conditions"""
        try:
            # Check minimum confidence requirement
            min_confidence = regime_config.get('min_confidence', 0.7)
            if signal.get('confidence', 0.0) < min_confidence:
                return False
            
            # Check volatility filter
            max_volatility = regime_config.get('max_volatility', 0.1)
            current_volatility = signal.get('metadata', {}).get('volatility', 0.02)
            if current_volatility > max_volatility:
                return False
            
            # Check market stress filter
            if market_stress > self.config.stress_threshold and signal.get('confidence', 0.0) < 0.8:
                return False
            
            # Check regime confidence filter
            if regime_confidence < 0.5 and signal.get('confidence', 0.0) < 0.75:
                return False
            
            # Check signal type compatibility
            allowed_signals = regime_config.get('allowed_signals', ['LONG', 'SHORT'])
            signal_type = signal.get('signal_type', 'HOLD')
            if signal_type not in allowed_signals:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Signal acceptance check failed: {e}")
            return True  # Accept signal if check fails
    
    def _adjust_signal_for_regime(
        self,
        signal: Dict[str, Any],
        regime: RegimeType,
        regime_confidence: float,
        regime_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adjust signal parameters based on market regime"""
        try:
            adjusted_signal = signal.copy()
            
            # Adjust position size based on regime
            size_multiplier = regime_config.get('position_size_multiplier', 1.0)
            current_size = signal.get('position_size', 0.1)
            adjusted_signal['position_size'] = current_size * size_multiplier
            
            # Adjust confidence based on regime alignment
            if regime == RegimeType.TRENDING and signal.get('signal_type') in ['LONG', 'SHORT']:
                # Boost trending signals in trending regime
                adjusted_signal['confidence'] = min(1.0, signal.get('confidence', 0.0) * 1.1)
            elif regime == RegimeType.VOLATILE:
                # Reduce confidence in volatile markets
                adjusted_signal['confidence'] = signal.get('confidence', 0.0) * 0.9
            
            # Add regime metadata
            metadata = signal.get('metadata', {})
            metadata.update({
                'regime': regime.value,
                'regime_confidence': regime_confidence,
                'regime_adjustment': size_multiplier,
                'phase2_enhanced': True
            })
            adjusted_signal['metadata'] = metadata
            
            return adjusted_signal
            
        except Exception as e:
            logger.error(f"Signal adjustment failed: {e}")
            return signal
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame) -> float:
        """Calculate trend strength using linear regression R-squared"""
        try:
            if len(market_data) < 20:
                return 0.0
            
            # Use recent data for trend calculation
            recent_data = market_data.tail(20)
            prices = recent_data['close'].values
            x = np.arange(len(prices))
            
            # Linear regression
            slope, intercept = np.polyfit(x, prices, 1)
            y_pred = slope * x + intercept
            
            # Calculate R-squared
            ss_res = np.sum((prices - y_pred) ** 2)
            ss_tot = np.sum((prices - np.mean(prices)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            
            return max(0.0, min(1.0, r_squared))
            
        except Exception as e:
            logger.error(f"Trend strength calculation failed: {e}")
            return 0.0
    
    def _calculate_mean_reversion_strength(self, market_data: pd.DataFrame) -> float:
        """Calculate mean reversion strength using autocorrelation"""
        try:
            if len(market_data) < 20:
                return 0.0
            
            # Calculate returns
            returns = market_data['close'].pct_change().dropna()
            
            if len(returns) < 10:
                return 0.0
            
            # Calculate autocorrelation at lag 1
            autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1]
            
            # Convert to mean reversion strength (negative autocorr = mean reversion)
            mean_reversion_strength = max(0.0, -autocorr) if autocorr < 0 else 0.0
            
            return mean_reversion_strength
            
        except Exception as e:
            logger.error(f"Mean reversion strength calculation failed: {e}")
            return 0.0
    
    def _calculate_market_stress(self, market_data: pd.DataFrame) -> float:
        """Calculate market stress indicator"""
        try:
            if len(market_data) < 20:
                return 0.5
            
            # Calculate multiple stress indicators
            returns = market_data['close'].pct_change().dropna()
            
            # Volatility stress
            volatility = returns.std()
            vol_stress = min(1.0, volatility / 0.05)  # Normalize to 5% volatility
            
            # Volume stress (if available)
            volume_stress = 0.5  # Default if no volume data
            if 'volume' in market_data.columns:
                recent_volume = market_data['volume'].tail(10).mean()
                avg_volume = market_data['volume'].mean()
                if avg_volume > 0:
                    volume_stress = min(1.0, recent_volume / avg_volume)
            
            # Price momentum stress
            recent_return = (market_data['close'].iloc[-1] / market_data['close'].iloc[-10] - 1)
            momentum_stress = min(1.0, abs(recent_return) / 0.1)  # Normalize to 10% move
            
            # Combine stress indicators
            total_stress = (vol_stress * 0.4 + volume_stress * 0.3 + momentum_stress * 0.3)
            
            return total_stress
            
        except Exception as e:
            logger.error(f"Market stress calculation failed: {e}")
            return 0.5
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """Get current filter statistics summary"""
        total_signals = self.filter_stats['signals_accepted'] + self.filter_stats['signals_filtered']
        acceptance_rate = (
            self.filter_stats['signals_accepted'] / total_signals 
            if total_signals > 0 else 0.0
        )
        
        return {
            'signals_accepted': self.filter_stats['signals_accepted'],
            'signals_filtered': self.filter_stats['signals_filtered'],
            'acceptance_rate': acceptance_rate,
            'regime_distribution': self.filter_stats['regime_distribution'],
            'total_regime_detections': len(self.regime_history)
        }
