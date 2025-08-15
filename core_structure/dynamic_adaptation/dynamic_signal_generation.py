"""
Dynamic Signal Generation - Template-Aware Adaptive Signal Generation
====================================================================

Template-inheritance-aware adaptive signal generation that dynamically adjusts
indicators, parameters, and weights based on market conditions and performance feedback.

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque

from strategy_templates.base import TemplateRegistry, TemplateCategory, TemplateInheritanceManager


class SignalAdaptationMode(Enum):
    """Signal adaptation modes"""
    CONSERVATIVE = "conservative"    # Minimal parameter adjustments
    MODERATE = "moderate"           # Balanced parameter adjustments
    AGGRESSIVE = "aggressive"       # Maximum parameter adjustments
    REGIME_BASED = "regime_based"   # Adapt based on market regime
    PERFORMANCE_BASED = "performance_based"  # Adapt based on performance


class IndicatorType(Enum):
    """Types of technical indicators"""
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    MOVING_AVERAGE = "moving_average"
    MOMENTUM = "momentum"
    STOCHASTIC = "stochastic"
    VOLUME = "volume"
    VOLATILITY = "volatility"


@dataclass
class IndicatorConfig:
    """Configuration for a technical indicator"""
    indicator_type: IndicatorType
    parameters: Dict[str, Any]
    weight: float
    enabled: bool = True
    adaptation_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    template_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalGenerationConfig:
    """Configuration for dynamic signal generation"""
    # Adaptation settings
    adaptation_mode: SignalAdaptationMode = SignalAdaptationMode.MODERATE
    adaptation_frequency: timedelta = timedelta(hours=1)
    min_confidence_threshold: float = 0.6
    
    # Template category settings
    category_adaptation_rules: Dict[TemplateCategory, Dict[str, Any]] = field(default_factory=lambda: {
        TemplateCategory.BASE: {
            'max_parameter_change': 0.1,      # 10% max change
            'adaptation_aggressiveness': 0.5,
            'min_performance_threshold': 0.7
        },
        TemplateCategory.SPECIFIC: {
            'max_parameter_change': 0.2,      # 20% max change
            'adaptation_aggressiveness': 0.8,
            'min_performance_threshold': 0.6
        },
        TemplateCategory.COMPOSITE: {
            'max_parameter_change': 0.3,      # 30% max change
            'adaptation_aggressiveness': 1.0,
            'min_performance_threshold': 0.5
        }
    })
    
    # Performance thresholds for adaptation
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'poor_performance_threshold': 0.4,
        'good_performance_threshold': 0.7,
        'excellent_performance_threshold': 0.9
    })
    
    # Market regime adaptation settings
    regime_adaptation_enabled: bool = True
    performance_adaptation_enabled: bool = True
    volatility_adaptation_enabled: bool = True


@dataclass
class AdaptationResult:
    """Result of signal generation adaptation"""
    success: bool
    adapted_indicators: Dict[str, IndicatorConfig]
    adaptation_magnitude: float
    confidence_score: float
    performance_improvement_estimate: float
    adaptation_reasons: List[str]
    template_compliance: bool
    execution_time_ms: float
    error_message: Optional[str] = None


class DynamicSignalGeneration:
    """
    Template-inheritance-aware adaptive signal generation
    """
    
    def __init__(self, 
                 template_registry: TemplateRegistry,
                 config: Optional[SignalGenerationConfig] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.config = config or SignalGenerationConfig()
        
        # Initialize components
        self.inheritance_manager = TemplateInheritanceManager(template_registry)
        
        # Signal generation state
        self.current_template_id: Optional[str] = None
        self.current_template_category: Optional[TemplateCategory] = None
        self.base_indicators: Dict[str, IndicatorConfig] = {}
        self.adapted_indicators: Dict[str, IndicatorConfig] = {}
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=100)
        self.adaptation_history: List[AdaptationResult] = []
        self.last_adaptation_time: Optional[datetime] = None
        
        # Market data tracking
        self.price_history: deque = deque(maxlen=200)
        self.volume_history: deque = deque(maxlen=200)
        self.volatility_history: deque = deque(maxlen=50)
        
        # Signal quality metrics
        self.signal_accuracy_history: deque = deque(maxlen=100)
        self.signal_performance_by_indicator: Dict[str, List[float]] = defaultdict(list)
        
        self.logger.info("Dynamic Signal Generation initialized")
    
    def initialize_for_template(self, template_id: str):
        """Initialize signal generation for a specific template"""
        try:
            template = self.template_registry.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            self.current_template_id = template_id
            self.current_template_category = template.metadata.category
            
            # Get base indicators from template and inheritance chain
            self.base_indicators = self._extract_template_indicators(template_id)
            self.adapted_indicators = {k: v for k, v in self.base_indicators.items()}
            
            # Reset state
            self.performance_history.clear()
            self.adaptation_history.clear()
            self.last_adaptation_time = None
            
            self.logger.info(f"Signal generation initialized for template {template_id} (category: {self.current_template_category.value})")
            self.logger.info(f"Loaded {len(self.base_indicators)} base indicators")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize signal generation: {e}")
            raise
    
    async def generate_adaptive_signals(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate signals with adaptive parameters based on current conditions
        """
        try:
            if not self.current_template_id:
                raise ValueError("Signal generation not initialized for template")
            
            start_time = datetime.now()
            
            # Update market data tracking
            self._update_market_data_tracking(market_data)
            
            # Check if adaptation is needed
            adaptation_needed, adaptation_reasons = self._check_adaptation_triggers(market_data)
            
            # Perform adaptation if needed
            if adaptation_needed:
                adaptation_result = await self._perform_signal_adaptation(market_data, adaptation_reasons)
                if adaptation_result.success:
                    self.adaptation_history.append(adaptation_result)
                    self.last_adaptation_time = datetime.now()
                    self.logger.info(f"Signal adaptation performed: {adaptation_result.adaptation_magnitude:.2%} magnitude")
            
            # Generate signals using current (possibly adapted) indicators
            signals = await self._generate_signals_with_indicators(market_data, self.adapted_indicators)
            
            # Calculate signal quality metrics
            signal_quality = self._calculate_signal_quality(signals, market_data)
            
            # Prepare result
            result = {
                'signals': signals,
                'signal_quality': signal_quality,
                'active_indicators': {k: self._indicator_to_dict(v) for k, v in self.adapted_indicators.items()},
                'adaptation_status': {
                    'last_adaptation': self.last_adaptation_time.isoformat() if self.last_adaptation_time else None,
                    'adaptations_count': len(self.adaptation_history),
                    'adaptation_needed': adaptation_needed,
                    'adaptation_reasons': adaptation_reasons
                },
                'template_info': {
                    'template_id': self.current_template_id,
                    'template_category': self.current_template_category.value,
                    'indicators_count': len(self.adapted_indicators)
                },
                'execution_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Signal generation failed: {e}"
            self.logger.error(error_msg)
            
            return {
                'signals': {},
                'signal_quality': {'overall_quality': 0.0, 'confidence': 0.0},
                'error': error_msg
            }
    
    def update_performance_feedback(self, signal_performance: Dict[str, float]):
        """Update performance feedback for signal adaptation"""
        try:
            # Add to performance history
            self.performance_history.append({
                'timestamp': datetime.now(),
                'performance': signal_performance.copy()
            })
            
            # Update indicator-specific performance if available
            if 'indicator_performance' in signal_performance:
                for indicator, performance in signal_performance['indicator_performance'].items():
                    if indicator in self.signal_performance_by_indicator:
                        self.signal_performance_by_indicator[indicator].append(performance)
                        # Keep only recent performance data
                        if len(self.signal_performance_by_indicator[indicator]) > 50:
                            self.signal_performance_by_indicator[indicator] = self.signal_performance_by_indicator[indicator][-50:]
            
            # Update overall signal accuracy
            if 'signal_accuracy' in signal_performance:
                self.signal_accuracy_history.append(signal_performance['signal_accuracy'])
            
            self.logger.debug(f"Performance feedback updated: {len(self.performance_history)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to update performance feedback: {e}")
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get comprehensive adaptation summary"""
        if not self.adaptation_history:
            return {
                'total_adaptations': 0,
                'average_improvement': 0.0,
                'adaptation_effectiveness': 0.0,
                'template_compliance_rate': 0.0
            }
        
        successful_adaptations = [a for a in self.adaptation_history if a.success]
        
        return {
            'total_adaptations': len(self.adaptation_history),
            'successful_adaptations': len(successful_adaptations),
            'success_rate': len(successful_adaptations) / len(self.adaptation_history),
            'average_improvement': np.mean([a.performance_improvement_estimate for a in successful_adaptations]) if successful_adaptations else 0.0,
            'average_confidence': np.mean([a.confidence_score for a in successful_adaptations]) if successful_adaptations else 0.0,
            'template_compliance_rate': np.mean([a.template_compliance for a in self.adaptation_history]),
            'adaptation_frequency': self._calculate_adaptation_frequency(),
            'indicator_performance': self._analyze_indicator_performance(),
            'current_signal_quality': self._calculate_current_signal_quality()
        }
    
    # Private helper methods
    def _extract_template_indicators(self, template_id: str) -> Dict[str, IndicatorConfig]:
        """Extract indicators from template and inheritance chain"""
        try:
            # Get resolved template with inheritance
            resolved_template = self.inheritance_manager.resolve_inheritance(template_id)
            if not resolved_template:
                self.logger.warning(f"Could not resolve inheritance for template {template_id}")
                template = self.template_registry.get_template(template_id)
                if not template:
                    return {}
                resolved_template = template
            
            indicators = {}
            
            # Extract indicators from template components
            if hasattr(resolved_template, 'components') and resolved_template.components:
                signal_config = resolved_template.components.get('signal_generator', {})
                indicators_config = signal_config.get('indicators', {})
                
                for indicator_name, indicator_data in indicators_config.items():
                    indicators[indicator_name] = self._create_indicator_config(indicator_name, indicator_data)
            
            # If no indicators found, create default indicators based on template category
            if not indicators:
                indicators = self._create_default_indicators()
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error extracting template indicators: {e}")
            return self._create_default_indicators()
    
    def _create_indicator_config(self, name: str, config_data: Dict[str, Any]) -> IndicatorConfig:
        """Create indicator configuration from template data"""
        try:
            # Map string names to IndicatorType enum
            indicator_type_map = {
                'rsi': IndicatorType.RSI,
                'macd': IndicatorType.MACD,
                'bollinger_bands': IndicatorType.BOLLINGER_BANDS,
                'moving_average': IndicatorType.MOVING_AVERAGE,
                'momentum': IndicatorType.MOMENTUM,
                'stochastic': IndicatorType.STOCHASTIC,
                'volume': IndicatorType.VOLUME,
                'volatility': IndicatorType.VOLATILITY
            }
            
            indicator_type = indicator_type_map.get(config_data.get('type', name.lower()), IndicatorType.RSI)
            
            # Extract parameters
            parameters = config_data.get('parameters', {})
            weight = config_data.get('weight', 1.0)
            enabled = config_data.get('enabled', True)
            
            # Create adaptation bounds based on template category
            adaptation_bounds = self._create_adaptation_bounds(indicator_type, parameters)
            
            return IndicatorConfig(
                indicator_type=indicator_type,
                parameters=parameters,
                weight=weight,
                enabled=enabled,
                adaptation_bounds=adaptation_bounds
            )
            
        except Exception as e:
            self.logger.error(f"Error creating indicator config for {name}: {e}")
            # Return default RSI indicator
            return IndicatorConfig(
                indicator_type=IndicatorType.RSI,
                parameters={'period': 14, 'overbought': 70, 'oversold': 30},
                weight=1.0,
                enabled=True,
                adaptation_bounds={'period': (5, 50), 'overbought': (60, 90), 'oversold': (10, 40)}
            )
    
    def _create_default_indicators(self) -> Dict[str, IndicatorConfig]:
        """Create default indicators based on template category"""
        default_indicators = {
            'rsi': IndicatorConfig(
                indicator_type=IndicatorType.RSI,
                parameters={'period': 14, 'overbought': 70, 'oversold': 30},
                weight=0.3,
                adaptation_bounds={'period': (5, 50), 'overbought': (60, 90), 'oversold': (10, 40)}
            ),
            'macd': IndicatorConfig(
                indicator_type=IndicatorType.MACD,
                parameters={'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                weight=0.4,
                adaptation_bounds={'fast_period': (5, 20), 'slow_period': (15, 50), 'signal_period': (5, 15)}
            ),
            'momentum': IndicatorConfig(
                indicator_type=IndicatorType.MOMENTUM,
                parameters={'lookback_period': 20},
                weight=0.3,
                adaptation_bounds={'lookback_period': (5, 50)}
            )
        }
        
        # Adjust weights based on template category
        if self.current_template_category == TemplateCategory.BASE:
            # More conservative weighting
            for indicator in default_indicators.values():
                indicator.weight *= 0.8
        elif self.current_template_category == TemplateCategory.COMPOSITE:
            # More aggressive weighting
            for indicator in default_indicators.values():
                indicator.weight *= 1.2
        
        return default_indicators
    
    def _create_adaptation_bounds(self, indicator_type: IndicatorType, base_parameters: Dict[str, Any]) -> Dict[str, Tuple[float, float]]:
        """Create adaptation bounds for indicator parameters"""
        bounds = {}
        
        if indicator_type == IndicatorType.RSI:
            bounds['period'] = (5, 50)
            bounds['overbought'] = (60, 90)
            bounds['oversold'] = (10, 40)
        elif indicator_type == IndicatorType.MACD:
            bounds['fast_period'] = (5, 25)
            bounds['slow_period'] = (15, 60)
            bounds['signal_period'] = (5, 20)
        elif indicator_type == IndicatorType.MOMENTUM:
            bounds['lookback_period'] = (5, 100)
        elif indicator_type == IndicatorType.BOLLINGER_BANDS:
            bounds['period'] = (10, 50)
            bounds['std_dev'] = (1.0, 3.0)
        elif indicator_type == IndicatorType.MOVING_AVERAGE:
            bounds['period'] = (5, 200)
        
        # Apply template category constraints
        category_rules = self.config.category_adaptation_rules.get(self.current_template_category, {})
        max_change = category_rules.get('max_parameter_change', 0.2)
        
        # Tighten bounds based on template category
        adjusted_bounds = {}
        for param, (min_val, max_val) in bounds.items():
            if param in base_parameters:
                base_val = base_parameters[param]
                if isinstance(base_val, (int, float)):
                    # Constrain bounds around base value
                    range_size = (max_val - min_val) * max_change
                    adjusted_min = max(min_val, base_val - range_size)
                    adjusted_max = min(max_val, base_val + range_size)
                    adjusted_bounds[param] = (adjusted_min, adjusted_max)
                else:
                    adjusted_bounds[param] = (min_val, max_val)
            else:
                adjusted_bounds[param] = (min_val, max_val)
        
        return adjusted_bounds
    
    def _update_market_data_tracking(self, market_data: Dict[str, Any]):
        """Update market data tracking for adaptation analysis"""
        try:
            # Update price history
            if 'price' in market_data:
                self.price_history.append(market_data['price'])
            elif 'prices' in market_data and market_data['prices']:
                self.price_history.append(market_data['prices'][-1])
            
            # Update volume history
            if 'volume' in market_data:
                self.volume_history.append(market_data['volume'])
            elif 'volumes' in market_data and market_data['volumes']:
                self.volume_history.append(market_data['volumes'][-1])
            
            # Calculate and update volatility
            if len(self.price_history) > 20:
                recent_prices = list(self.price_history)[-20:]
                returns = np.diff(np.log(recent_prices))
                volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
                self.volatility_history.append(volatility)
                
        except Exception as e:
            self.logger.error(f"Error updating market data tracking: {e}")
    
    def _check_adaptation_triggers(self, market_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if signal adaptation is needed"""
        reasons = []
        
        try:
            # Check adaptation frequency
            if self.last_adaptation_time:
                time_since_last = datetime.now() - self.last_adaptation_time
                if time_since_last < self.config.adaptation_frequency:
                    return False, []
            
            # Check performance degradation
            if self._check_performance_degradation():
                reasons.append("performance_degradation")
            
            # Check market regime change
            if self._check_market_regime_change():
                reasons.append("market_regime_change")
            
            # Check volatility spike
            if self._check_volatility_spike():
                reasons.append("volatility_spike")
            
            # Check signal quality degradation
            if self._check_signal_quality_degradation():
                reasons.append("signal_quality_degradation")
            
            return len(reasons) > 0, reasons
            
        except Exception as e:
            self.logger.error(f"Error checking adaptation triggers: {e}")
            return False, []
    
    def _check_performance_degradation(self) -> bool:
        """Check if recent performance indicates adaptation is needed"""
        if len(self.performance_history) < 5:
            return False
        
        recent_performance = [p['performance'] for p in list(self.performance_history)[-5:]]
        avg_recent_performance = np.mean([p.get('overall_score', 0.5) for p in recent_performance])
        
        threshold = self.config.performance_thresholds['poor_performance_threshold']
        return avg_recent_performance < threshold
    
    def _check_market_regime_change(self) -> bool:
        """Check if market regime has changed significantly"""
        if len(self.volatility_history) < 10:
            return False
        
        recent_vol = np.mean(list(self.volatility_history)[-5:])
        historical_vol = np.mean(list(self.volatility_history)[:-5])
        
        # Significant volatility change indicates regime change
        vol_change_ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
        return vol_change_ratio > 1.5 or vol_change_ratio < 0.67
    
    def _check_volatility_spike(self) -> bool:
        """Check for sudden volatility spikes"""
        if len(self.volatility_history) < 3:
            return False
        
        current_vol = self.volatility_history[-1]
        avg_vol = np.mean(list(self.volatility_history)[:-1])
        
        return current_vol > avg_vol * 1.8  # 80% increase threshold
    
    def _check_signal_quality_degradation(self) -> bool:
        """Check if signal quality has degraded"""
        if len(self.signal_accuracy_history) < 10:
            return False
        
        recent_accuracy = np.mean(list(self.signal_accuracy_history)[-5:])
        historical_accuracy = np.mean(list(self.signal_accuracy_history)[:-5])
        
        return recent_accuracy < historical_accuracy * 0.85  # 15% degradation threshold
    
    async def _perform_signal_adaptation(self, market_data: Dict[str, Any], reasons: List[str]) -> AdaptationResult:
        """Perform signal adaptation based on triggers"""
        try:
            start_time = datetime.now()
            
            # Create new adapted indicators
            new_indicators = {}
            total_adaptation_magnitude = 0.0
            adaptation_success = True
            template_compliance = True
            
            for indicator_name, indicator_config in self.adapted_indicators.items():
                adapted_config = await self._adapt_indicator(indicator_config, market_data, reasons)
                new_indicators[indicator_name] = adapted_config
                
                # Calculate adaptation magnitude for this indicator
                magnitude = self._calculate_indicator_adaptation_magnitude(indicator_config, adapted_config)
                total_adaptation_magnitude += magnitude
            
            # Average adaptation magnitude
            avg_adaptation_magnitude = total_adaptation_magnitude / len(new_indicators) if new_indicators else 0.0
            
            # Validate template compliance
            template_compliance = self._validate_template_compliance(new_indicators)
            
            if template_compliance:
                # Apply adaptations
                self.adapted_indicators = new_indicators
                
                # Estimate performance improvement
                improvement_estimate = self._estimate_performance_improvement(reasons, avg_adaptation_magnitude)
                
                # Calculate confidence score
                confidence_score = self._calculate_adaptation_confidence(reasons, avg_adaptation_magnitude)
                
                result = AdaptationResult(
                    success=True,
                    adapted_indicators=new_indicators,
                    adaptation_magnitude=avg_adaptation_magnitude,
                    confidence_score=confidence_score,
                    performance_improvement_estimate=improvement_estimate,
                    adaptation_reasons=reasons,
                    template_compliance=True,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000
                )
                
            else:
                result = AdaptationResult(
                    success=False,
                    adapted_indicators=self.adapted_indicators,
                    adaptation_magnitude=0.0,
                    confidence_score=0.0,
                    performance_improvement_estimate=0.0,
                    adaptation_reasons=reasons,
                    template_compliance=False,
                    execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    error_message="Template compliance validation failed"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Signal adaptation failed: {e}"
            self.logger.error(error_msg)
            
            return AdaptationResult(
                success=False,
                adapted_indicators=self.adapted_indicators,
                adaptation_magnitude=0.0,
                confidence_score=0.0,
                performance_improvement_estimate=0.0,
                adaptation_reasons=reasons,
                template_compliance=False,
                execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=error_msg
            )
    
    async def _adapt_indicator(self, indicator_config: IndicatorConfig, market_data: Dict[str, Any], reasons: List[str]) -> IndicatorConfig:
        """Adapt a single indicator based on conditions"""
        new_config = IndicatorConfig(
            indicator_type=indicator_config.indicator_type,
            parameters=indicator_config.parameters.copy(),
            weight=indicator_config.weight,
            enabled=indicator_config.enabled,
            adaptation_bounds=indicator_config.adaptation_bounds,
            template_constraints=indicator_config.template_constraints
        )
        
        # Get category adaptation rules
        category_rules = self.config.category_adaptation_rules.get(self.current_template_category, {})
        aggressiveness = category_rules.get('adaptation_aggressiveness', 0.8)
        
        # Adapt parameters based on reasons
        if 'performance_degradation' in reasons:
            new_config = self._adapt_for_performance_degradation(new_config, aggressiveness)
        
        if 'market_regime_change' in reasons:
            new_config = self._adapt_for_regime_change(new_config, market_data, aggressiveness)
        
        if 'volatility_spike' in reasons:
            new_config = self._adapt_for_volatility_spike(new_config, aggressiveness)
        
        if 'signal_quality_degradation' in reasons:
            new_config = self._adapt_for_signal_quality(new_config, aggressiveness)
        
        # Ensure parameters stay within bounds
        new_config = self._enforce_parameter_bounds(new_config)
        
        return new_config
    
    def _adapt_for_performance_degradation(self, config: IndicatorConfig, aggressiveness: float) -> IndicatorConfig:
        """Adapt indicator for performance degradation"""
        
        if config.indicator_type == IndicatorType.RSI:
            # Make RSI more sensitive
            if 'period' in config.parameters:
                current_period = config.parameters['period']
                new_period = max(5, int(current_period * (1 - 0.2 * aggressiveness)))
                config.parameters['period'] = new_period
            
            # Adjust overbought/oversold levels
            if 'overbought' in config.parameters:
                config.parameters['overbought'] = min(90, config.parameters['overbought'] + 5 * aggressiveness)
            if 'oversold' in config.parameters:
                config.parameters['oversold'] = max(10, config.parameters['oversold'] - 5 * aggressiveness)
        
        elif config.indicator_type == IndicatorType.MACD:
            # Make MACD more responsive
            if 'fast_period' in config.parameters:
                current_fast = config.parameters['fast_period']
                config.parameters['fast_period'] = max(5, int(current_fast * (1 - 0.15 * aggressiveness)))
            
            if 'slow_period' in config.parameters:
                current_slow = config.parameters['slow_period']
                config.parameters['slow_period'] = max(15, int(current_slow * (1 - 0.1 * aggressiveness)))
        
        # Increase weight for better performing indicators
        indicator_performance = self.signal_performance_by_indicator.get(config.indicator_type.value, [])
        if indicator_performance:
            avg_performance = np.mean(indicator_performance)
            if avg_performance > 0.6:
                config.weight *= (1 + 0.1 * aggressiveness)
        
        return config
    
    def _adapt_for_regime_change(self, config: IndicatorConfig, market_data: Dict[str, Any], aggressiveness: float) -> IndicatorConfig:
        """Adapt indicator for market regime change"""
        
        # Determine if trending or mean-reverting based on recent price action
        if len(self.price_history) > 20:
            recent_prices = list(self.price_history)[-20:]
            price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            if abs(price_trend) > 0.05:  # Trending market
                if config.indicator_type == IndicatorType.RSI:
                    # Longer period for trending markets
                    if 'period' in config.parameters:
                        config.parameters['period'] = min(50, int(config.parameters['period'] * (1 + 0.3 * aggressiveness)))
                
                elif config.indicator_type == IndicatorType.MACD:
                    # Faster MACD for trending markets
                    if 'fast_period' in config.parameters:
                        config.parameters['fast_period'] = max(5, int(config.parameters['fast_period'] * (1 - 0.2 * aggressiveness)))
                
                # Increase momentum indicator weight
                if config.indicator_type == IndicatorType.MOMENTUM:
                    config.weight *= (1 + 0.2 * aggressiveness)
            
            else:  # Mean-reverting market
                if config.indicator_type == IndicatorType.RSI:
                    # Shorter period for mean-reverting markets
                    if 'period' in config.parameters:
                        config.parameters['period'] = max(5, int(config.parameters['period'] * (1 - 0.2 * aggressiveness)))
                
                # Increase RSI weight for mean reversion
                if config.indicator_type == IndicatorType.RSI:
                    config.weight *= (1 + 0.15 * aggressiveness)
        
        return config
    
    def _adapt_for_volatility_spike(self, config: IndicatorConfig, aggressiveness: float) -> IndicatorConfig:
        """Adapt indicator for volatility spikes"""
        
        # Generally make indicators less sensitive during high volatility
        if config.indicator_type == IndicatorType.RSI:
            if 'period' in config.parameters:
                config.parameters['period'] = min(50, int(config.parameters['period'] * (1 + 0.25 * aggressiveness)))
            
            # Widen overbought/oversold bands
            if 'overbought' in config.parameters:
                config.parameters['overbought'] = min(90, config.parameters['overbought'] + 10 * aggressiveness)
            if 'oversold' in config.parameters:
                config.parameters['oversold'] = max(10, config.parameters['oversold'] - 10 * aggressiveness)
        
        elif config.indicator_type == IndicatorType.MACD:
            # Slower MACD during high volatility
            if 'fast_period' in config.parameters:
                config.parameters['fast_period'] = min(25, int(config.parameters['fast_period'] * (1 + 0.2 * aggressiveness)))
            if 'slow_period' in config.parameters:
                config.parameters['slow_period'] = min(60, int(config.parameters['slow_period'] * (1 + 0.15 * aggressiveness)))
        
        # Reduce overall weight during high volatility
        config.weight *= (1 - 0.1 * aggressiveness)
        
        return config
    
    def _adapt_for_signal_quality(self, config: IndicatorConfig, aggressiveness: float) -> IndicatorConfig:
        """Adapt indicator for signal quality degradation"""
        
        # Check individual indicator performance
        indicator_performance = self.signal_performance_by_indicator.get(config.indicator_type.value, [])
        
        if indicator_performance:
            avg_performance = np.mean(indicator_performance)
            
            if avg_performance < 0.4:  # Poor performance
                # Reduce weight significantly
                config.weight *= (1 - 0.3 * aggressiveness)
                
                # Make indicator more conservative
                if config.indicator_type == IndicatorType.RSI:
                    if 'period' in config.parameters:
                        config.parameters['period'] = min(50, int(config.parameters['period'] * (1 + 0.3 * aggressiveness)))
                
            elif avg_performance > 0.7:  # Good performance
                # Increase weight
                config.weight *= (1 + 0.2 * aggressiveness)
        
        return config
    
    def _enforce_parameter_bounds(self, config: IndicatorConfig) -> IndicatorConfig:
        """Ensure parameters stay within allowed bounds"""
        
        for param, value in config.parameters.items():
            if param in config.adaptation_bounds:
                min_val, max_val = config.adaptation_bounds[param]
                if isinstance(value, (int, float)):
                    config.parameters[param] = max(min_val, min(max_val, value))
                    
                    # Ensure integer parameters remain integers
                    if isinstance(value, int):
                        config.parameters[param] = int(config.parameters[param])
        
        # Ensure weight stays reasonable
        config.weight = max(0.1, min(2.0, config.weight))
        
        return config
    
    def _validate_template_compliance(self, indicators: Dict[str, IndicatorConfig]) -> bool:
        """Validate that adapted indicators comply with template constraints"""
        
        try:
            # Check if any constraints are defined in the template
            for indicator_name, config in indicators.items():
                if config.template_constraints:
                    for constraint, limit in config.template_constraints.items():
                        if constraint in config.parameters:
                            if not self._check_constraint_compliance(config.parameters[constraint], limit):
                                return False
            
            # Check category-specific limits
            category_rules = self.config.category_adaptation_rules.get(self.current_template_category, {})
            max_change = category_rules.get('max_parameter_change', 0.3)
            
            # Compare with base indicators
            for indicator_name, adapted_config in indicators.items():
                if indicator_name in self.base_indicators:
                    base_config = self.base_indicators[indicator_name]
                    
                    # Check parameter changes
                    for param, new_value in adapted_config.parameters.items():
                        if param in base_config.parameters:
                            base_value = base_config.parameters[param]
                            if isinstance(base_value, (int, float)) and base_value != 0:
                                change_ratio = abs((new_value - base_value) / base_value)
                                if change_ratio > max_change:
                                    return False
                    
                    # Check weight changes
                    weight_change_ratio = abs((adapted_config.weight - base_config.weight) / base_config.weight) if base_config.weight != 0 else 0
                    if weight_change_ratio > max_change:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating template compliance: {e}")
            return False
    
    def _check_constraint_compliance(self, value: Any, limit: Any) -> bool:
        """Check if a parameter value complies with constraint"""
        
        if isinstance(limit, dict):
            if 'min' in limit and value < limit['min']:
                return False
            if 'max' in limit and value > limit['max']:
                return False
        elif isinstance(limit, (list, tuple)) and len(limit) == 2:
            if value < limit[0] or value > limit[1]:
                return False
        
        return True
    
    def _calculate_indicator_adaptation_magnitude(self, original: IndicatorConfig, adapted: IndicatorConfig) -> float:
        """Calculate adaptation magnitude for a single indicator"""
        
        total_change = 0.0
        param_count = 0
        
        # Parameter changes
        for param, new_value in adapted.parameters.items():
            if param in original.parameters:
                original_value = original.parameters[param]
                if isinstance(original_value, (int, float)) and original_value != 0:
                    change_ratio = abs((new_value - original_value) / original_value)
                    total_change += change_ratio
                    param_count += 1
        
        # Weight change
        if original.weight != 0:
            weight_change = abs((adapted.weight - original.weight) / original.weight)
            total_change += weight_change
            param_count += 1
        
        return total_change / param_count if param_count > 0 else 0.0
    
    def _estimate_performance_improvement(self, reasons: List[str], adaptation_magnitude: float) -> float:
        """Estimate potential performance improvement from adaptation"""
        
        base_improvement = adaptation_magnitude * 0.5  # 50% of adaptation magnitude
        
        # Adjust based on adaptation reasons
        reason_multipliers = {
            'performance_degradation': 1.5,
            'market_regime_change': 1.2,
            'volatility_spike': 1.0,
            'signal_quality_degradation': 1.3
        }
        
        total_multiplier = 1.0
        for reason in reasons:
            total_multiplier *= reason_multipliers.get(reason, 1.0)
        
        # Apply template category modifier
        category_modifiers = {
            TemplateCategory.BASE: 0.8,      # Conservative estimate
            TemplateCategory.SPECIFIC: 1.0,  # Standard estimate
            TemplateCategory.COMPOSITE: 1.2  # Optimistic estimate
        }
        
        category_modifier = category_modifiers.get(self.current_template_category, 1.0)
        
        return min(0.5, base_improvement * total_multiplier * category_modifier)  # Cap at 50% improvement
    
    def _calculate_adaptation_confidence(self, reasons: List[str], adaptation_magnitude: float) -> float:
        """Calculate confidence in adaptation decision"""
        
        base_confidence = 0.7  # Base confidence
        
        # Adjust based on number of performance history points
        if len(self.performance_history) > 20:
            base_confidence += 0.1
        elif len(self.performance_history) < 5:
            base_confidence -= 0.2
        
        # Adjust based on adaptation magnitude
        if adaptation_magnitude > 0.3:
            base_confidence -= 0.1  # Large changes are riskier
        elif adaptation_magnitude < 0.1:
            base_confidence -= 0.05  # Very small changes may not help
        
        # Adjust based on reasons
        reason_confidence_adjustments = {
            'performance_degradation': 0.1,
            'market_regime_change': 0.05,
            'volatility_spike': 0.0,
            'signal_quality_degradation': 0.08
        }
        
        for reason in reasons:
            base_confidence += reason_confidence_adjustments.get(reason, 0.0)
        
        return max(0.1, min(1.0, base_confidence))
    
    async def _generate_signals_with_indicators(self, market_data: Dict[str, Any], indicators: Dict[str, IndicatorConfig]) -> Dict[str, Any]:
        """Generate trading signals using current indicators"""
        
        signals = {}
        
        try:
            # Get price data
            if 'prices' in market_data and market_data['prices']:
                prices = np.array(market_data['prices'])
            elif 'price' in market_data:
                # Use price history if available
                if len(self.price_history) > 0:
                    prices = np.array(list(self.price_history))
                else:
                    prices = np.array([market_data['price']])
            else:
                return {'error': 'No price data available'}
            
            # Generate signals for each indicator
            for indicator_name, config in indicators.items():
                if config.enabled:
                    signal_value = await self._calculate_indicator_signal(config, prices, market_data)
                    if signal_value is not None:
                        signals[indicator_name] = {
                            'value': signal_value,
                            'weight': config.weight,
                            'type': config.indicator_type.value,
                            'parameters': config.parameters
                        }
            
            # Calculate combined signal
            if signals:
                combined_signal = self._calculate_combined_signal(signals)
                signals['combined'] = combined_signal
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return {'error': str(e)}
    
    async def _calculate_indicator_signal(self, config: IndicatorConfig, prices: np.ndarray, market_data: Dict[str, Any]) -> Optional[float]:
        """Calculate signal value for a specific indicator"""
        
        try:
            if len(prices) < 2:
                return 0.0
            
            if config.indicator_type == IndicatorType.RSI:
                return self._calculate_rsi_signal(prices, config.parameters)
            elif config.indicator_type == IndicatorType.MACD:
                return self._calculate_macd_signal(prices, config.parameters)
            elif config.indicator_type == IndicatorType.MOMENTUM:
                return self._calculate_momentum_signal(prices, config.parameters)
            elif config.indicator_type == IndicatorType.MOVING_AVERAGE:
                return self._calculate_ma_signal(prices, config.parameters)
            elif config.indicator_type == IndicatorType.BOLLINGER_BANDS:
                return self._calculate_bb_signal(prices, config.parameters)
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Error calculating {config.indicator_type.value} signal: {e}")
            return 0.0
    
    def _calculate_rsi_signal(self, prices: np.ndarray, params: Dict[str, Any]) -> float:
        """Calculate RSI signal"""
        period = params.get('period', 14)
        overbought = params.get('overbought', 70)
        oversold = params.get('oversold', 30)
        
        if len(prices) < period + 1:
            return 0.0
        
        # Calculate price changes
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Generate signal
        if rsi > overbought:
            return -1.0  # Sell signal
        elif rsi < oversold:
            return 1.0   # Buy signal
        else:
            # Interpolate between 0 and signal strength
            if rsi > 50:
                return -(rsi - 50) / (overbought - 50)
            else:
                return (50 - rsi) / (50 - oversold)
    
    def _calculate_macd_signal(self, prices: np.ndarray, params: Dict[str, Any]) -> float:
        """Calculate MACD signal"""
        fast_period = params.get('fast_period', 12)
        slow_period = params.get('slow_period', 26)
        signal_period = params.get('signal_period', 9)
        
        if len(prices) < slow_period + signal_period:
            return 0.0
        
        # Calculate EMAs
        fast_ema = self._calculate_ema(prices, fast_period)
        slow_ema = self._calculate_ema(prices, slow_period)
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        if len(macd_line) < signal_period:
            return 0.0
        
        signal_line = self._calculate_ema(macd_line, signal_period)
        
        # Generate signal based on MACD crossover
        if len(macd_line) < 2 or len(signal_line) < 2:
            return 0.0
        
        current_diff = macd_line[-1] - signal_line[-1]
        previous_diff = macd_line[-2] - signal_line[-2]
        
        # Crossover signals
        if previous_diff <= 0 and current_diff > 0:
            return 1.0   # Bullish crossover
        elif previous_diff >= 0 and current_diff < 0:
            return -1.0  # Bearish crossover
        else:
            # Continuous signal based on difference magnitude
            return np.tanh(current_diff / np.std(macd_line[-20:] if len(macd_line) > 20 else macd_line))
    
    def _calculate_momentum_signal(self, prices: np.ndarray, params: Dict[str, Any]) -> float:
        """Calculate momentum signal"""
        lookback = params.get('lookback_period', 20)
        
        if len(prices) < lookback + 1:
            return 0.0
        
        # Calculate momentum as rate of change
        momentum = (prices[-1] - prices[-lookback]) / prices[-lookback]
        
        # Normalize momentum signal
        return np.tanh(momentum * 10)  # Scale and bound between -1 and 1
    
    def _calculate_ma_signal(self, prices: np.ndarray, params: Dict[str, Any]) -> float:
        """Calculate moving average signal"""
        period = params.get('period', 20)
        
        if len(prices) < period:
            return 0.0
        
        ma = np.mean(prices[-period:])
        current_price = prices[-1]
        
        # Signal based on price relative to MA
        deviation = (current_price - ma) / ma
        return np.tanh(deviation * 20)  # Scale and bound
    
    def _calculate_bb_signal(self, prices: np.ndarray, params: Dict[str, Any]) -> float:
        """Calculate Bollinger Bands signal"""
        period = params.get('period', 20)
        std_dev = params.get('std_dev', 2.0)
        
        if len(prices) < period:
            return 0.0
        
        ma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)
        
        current_price = prices[-1]
        
        if current_price > upper_band:
            return -1.0  # Sell signal (overbought)
        elif current_price < lower_band:
            return 1.0   # Buy signal (oversold)
        else:
            # Interpolate position within bands
            band_position = (current_price - lower_band) / (upper_band - lower_band)
            return 1.0 - 2.0 * band_position  # Convert to -1 to 1 range
    
    def _calculate_ema(self, values: np.ndarray, period: int) -> np.ndarray:
        """Calculate exponential moving average"""
        if len(values) < period:
            return values
        
        alpha = 2.0 / (period + 1)
        ema = np.zeros_like(values)
        ema[0] = values[0]
        
        for i in range(1, len(values)):
            ema[i] = alpha * values[i] + (1 - alpha) * ema[i-1]
        
        return ema
    
    def _calculate_combined_signal(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate combined signal from all indicators"""
        
        total_weight = 0.0
        weighted_signal = 0.0
        
        for signal_name, signal_data in signals.items():
            if signal_name != 'combined' and 'value' in signal_data and 'weight' in signal_data:
                weight = signal_data['weight']
                value = signal_data['value']
                
                weighted_signal += value * weight
                total_weight += weight
        
        if total_weight > 0:
            combined_value = weighted_signal / total_weight
        else:
            combined_value = 0.0
        
        # Calculate signal strength
        signal_strength = abs(combined_value)
        
        # Determine signal direction
        if combined_value > 0.1:
            signal_direction = 'buy'
        elif combined_value < -0.1:
            signal_direction = 'sell'
        else:
            signal_direction = 'hold'
        
        return {
            'value': combined_value,
            'strength': signal_strength,
            'direction': signal_direction,
            'confidence': min(1.0, signal_strength * 2),  # Scale confidence
            'contributing_signals': len([s for s in signals.values() if s.get('value', 0) != 0])
        }
    
    def _calculate_signal_quality(self, signals: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate signal quality metrics"""
        
        try:
            if not signals or 'combined' not in signals:
                return {'overall_quality': 0.0, 'confidence': 0.0}
            
            combined_signal = signals['combined']
            signal_strength = combined_signal.get('strength', 0.0)
            contributing_signals = combined_signal.get('contributing_signals', 0)
            
            # Quality factors
            strength_quality = min(1.0, signal_strength * 2)  # Stronger signals are better
            consensus_quality = min(1.0, contributing_signals / len(self.adapted_indicators))  # More consensus is better
            
            # Historical accuracy factor
            if len(self.signal_accuracy_history) > 0:
                accuracy_quality = np.mean(list(self.signal_accuracy_history))
            else:
                accuracy_quality = 0.5  # Default
            
            # Market condition factor
            market_volatility = self.volatility_history[-1] if self.volatility_history else 0.2
            volatility_quality = 1.0 / (1.0 + market_volatility)  # Lower volatility = higher quality
            
            # Overall quality
            overall_quality = (strength_quality * 0.3 + 
                             consensus_quality * 0.3 + 
                             accuracy_quality * 0.2 + 
                             volatility_quality * 0.2)
            
            return {
                'overall_quality': overall_quality,
                'confidence': combined_signal.get('confidence', 0.0),
                'signal_strength': signal_strength,
                'consensus_level': consensus_quality,
                'historical_accuracy': accuracy_quality,
                'market_volatility_factor': volatility_quality,
                'contributing_indicators': contributing_signals
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating signal quality: {e}")
            return {'overall_quality': 0.0, 'confidence': 0.0}
    
    def _calculate_adaptation_frequency(self) -> float:
        """Calculate adaptation frequency (adaptations per hour)"""
        if len(self.adaptation_history) < 2:
            return 0.0
        
        first_adaptation = self.adaptation_history[0]
        last_adaptation = self.adaptation_history[-1]
        
        # This would need actual timestamps in a real implementation
        time_span_hours = 24  # Assume 24 hours for demo
        
        return len(self.adaptation_history) / time_span_hours
    
    def _analyze_indicator_performance(self) -> Dict[str, Dict[str, float]]:
        """Analyze performance of individual indicators"""
        performance_analysis = {}
        
        for indicator_type, performance_history in self.signal_performance_by_indicator.items():
            if performance_history:
                performance_analysis[indicator_type] = {
                    'average_performance': np.mean(performance_history),
                    'performance_consistency': 1.0 - np.std(performance_history),
                    'recent_trend': self._calculate_performance_trend(performance_history),
                    'usage_count': len(performance_history)
                }
        
        return performance_analysis
    
    def _calculate_performance_trend(self, performance_history: List[float]) -> float:
        """Calculate performance trend (positive = improving, negative = declining)"""
        if len(performance_history) < 3:
            return 0.0
        
        # Simple linear regression slope
        x = np.arange(len(performance_history))
        y = np.array(performance_history)
        slope, _ = np.polyfit(x, y, 1)
        
        return slope
    
    def _calculate_current_signal_quality(self) -> float:
        """Calculate current overall signal quality"""
        if len(self.signal_accuracy_history) == 0:
            return 0.5
        
        # Weight recent performance more heavily
        weights = np.exp(np.linspace(-1, 0, len(self.signal_accuracy_history)))
        weights = weights / np.sum(weights)
        
        return np.average(list(self.signal_accuracy_history), weights=weights)
    
    def _indicator_to_dict(self, indicator: IndicatorConfig) -> Dict[str, Any]:
        """Convert indicator config to dictionary for serialization"""
        return {
            'type': indicator.indicator_type.value,
            'parameters': indicator.parameters,
            'weight': indicator.weight,
            'enabled': indicator.enabled,
            'adaptation_bounds': indicator.adaptation_bounds,
            'template_constraints': indicator.template_constraints
        }
