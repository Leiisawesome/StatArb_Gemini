"""
Category-Aware Core Components
=============================

Specialized core components that adapt their behavior based on
template categories, providing optimized performance for each tier.

Author: Pro Quant Desk Trader
"""

import logging
import asyncio
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

from strategy_templates.base import TemplateCategory, BaseTemplate

logger = logging.getLogger(__name__)

class AdaptationStrategy(Enum):
    """Component adaptation strategies"""
    PERFORMANCE_OPTIMIZED = "performance_optimized"    # Optimize for speed
    ACCURACY_OPTIMIZED = "accuracy_optimized"          # Optimize for precision
    BALANCED = "balanced"                               # Balance speed and accuracy
    RESOURCE_EFFICIENT = "resource_efficient"          # Minimize resource usage

@dataclass
class ComponentAdaptationConfig:
    """Configuration for component adaptation"""
    target_category: TemplateCategory
    adaptation_strategy: AdaptationStrategy = AdaptationStrategy.BALANCED
    
    # Performance targets
    max_latency_ms: float = 100.0
    min_accuracy_threshold: float = 0.8
    max_memory_mb: float = 100.0
    max_cpu_percent: float = 50.0
    
    # Category-specific settings
    enable_caching: bool = True
    cache_size: int = 1000
    parallel_processing: bool = False
    batch_size: int = 1

class CategoryAwareComponent(ABC):
    """Base class for category-aware components"""
    
    def __init__(self, template: BaseTemplate, config: ComponentAdaptationConfig):
        self.template = template
        self.config = config
        self.category = template.metadata.category
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{self.category.value}")
        
        # Adaptation state
        self.current_strategy = config.adaptation_strategy
        self.performance_metrics = {}
        self.adaptation_history = []
        
        # Component state
        self.is_initialized = False
        self.cache = {} if config.enable_caching else None
        
    @abstractmethod
    async def initialize(self):
        """Initialize component with category-specific optimizations"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input with category-aware optimizations"""
        pass
    
    async def adapt_to_category(self):
        """Adapt component behavior based on template category"""
        
        if self.category == TemplateCategory.BASE:
            await self._adapt_for_base_category()
        elif self.category == TemplateCategory.SPECIFIC:
            await self._adapt_for_specific_category()
        elif self.category == TemplateCategory.COMPOSITE:
            await self._adapt_for_composite_category()
    
    async def _adapt_for_base_category(self):
        """Adapt for BASE category - prioritize speed and simplicity"""
        
        self.current_strategy = AdaptationStrategy.PERFORMANCE_OPTIMIZED
        self.config.max_latency_ms = 50.0
        self.config.cache_size = 500
        self.config.parallel_processing = False
        
        self.logger.debug("Adapted for BASE category - performance optimized")
    
    async def _adapt_for_specific_category(self):
        """Adapt for SPECIFIC category - balance accuracy and performance"""
        
        self.current_strategy = AdaptationStrategy.BALANCED
        self.config.max_latency_ms = 100.0
        self.config.cache_size = 1000
        self.config.parallel_processing = False
        
        self.logger.debug("Adapted for SPECIFIC category - balanced approach")
    
    async def _adapt_for_composite_category(self):
        """Adapt for COMPOSITE category - prioritize accuracy and sophistication"""
        
        self.current_strategy = AdaptationStrategy.ACCURACY_OPTIMIZED
        self.config.max_latency_ms = 200.0
        self.config.cache_size = 2000
        self.config.parallel_processing = True
        
        self.logger.debug("Adapted for COMPOSITE category - accuracy optimized")
    
    def _should_use_cache(self, cache_key: str) -> bool:
        """Determine if caching should be used"""
        
        if not self.cache:
            return False
        
        # Category-specific caching logic
        if self.category == TemplateCategory.BASE:
            return True  # Aggressive caching for base templates
        elif self.category == TemplateCategory.SPECIFIC:
            return len(self.cache) < self.config.cache_size
        else:  # COMPOSITE
            return len(self.cache) < self.config.cache_size * 2
    
    def _get_cache_key(self, input_data: Any) -> str:
        """Generate cache key for input data"""
        
        return str(hash(str(input_data)))[:16]
    
    async def update_performance_metrics(self, execution_time_ms: float, accuracy: float):
        """Update component performance metrics"""
        
        self.performance_metrics.update({
            'last_execution_time_ms': execution_time_ms,
            'last_accuracy': accuracy,
            'avg_execution_time_ms': self.performance_metrics.get('avg_execution_time_ms', execution_time_ms),
            'avg_accuracy': self.performance_metrics.get('avg_accuracy', accuracy)
        })
        
        # Exponential smoothing
        alpha = 0.1
        self.performance_metrics['avg_execution_time_ms'] = (
            (1 - alpha) * self.performance_metrics['avg_execution_time_ms'] + 
            alpha * execution_time_ms
        )
        self.performance_metrics['avg_accuracy'] = (
            (1 - alpha) * self.performance_metrics['avg_accuracy'] + 
            alpha * accuracy
        )

class CategoryAwareSignalProcessor(CategoryAwareComponent):
    """Category-aware signal processing component"""
    
    async def initialize(self):
        """Initialize signal processor"""
        
        await self.adapt_to_category()
        
        # Category-specific initialization
        if self.category == TemplateCategory.BASE:
            self.signal_filters = ['simple_moving_average']
            self.lookback_periods = [5, 10]
        elif self.category == TemplateCategory.SPECIFIC:
            self.signal_filters = ['exponential_moving_average', 'rsi', 'macd']
            self.lookback_periods = [5, 10, 20]
        else:  # COMPOSITE
            self.signal_filters = ['exponential_moving_average', 'rsi', 'macd', 'bollinger_bands', 'stochastic']
            self.lookback_periods = [5, 10, 20, 50]
        
        self.is_initialized = True
        self.logger.info(f"Signal processor initialized for {self.category.value}")
    
    async def process(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Process market data to generate signals"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(market_data)
        if self._should_use_cache(cache_key) and cache_key in self.cache:
            result = self.cache[cache_key]
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.update_performance_metrics(execution_time, 1.0)  # Cache hit = perfect accuracy
            return result
        
        # Generate signals based on category
        signals = await self._generate_category_signals(market_data)
        
        # Cache result
        if self.cache and self._should_use_cache(cache_key):
            self.cache[cache_key] = signals
        
        # Update performance metrics
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        signal_quality = self._assess_signal_quality(signals)
        await self.update_performance_metrics(execution_time, signal_quality)
        
        return signals
    
    async def _generate_category_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate signals based on template category"""
        
        symbols = market_data.get('symbols', ['AAPL', 'GOOGL', 'MSFT'])
        signals = {}
        
        for symbol in symbols:
            if self.category == TemplateCategory.BASE:
                signals[symbol] = await self._generate_base_signal(symbol, market_data)
            elif self.category == TemplateCategory.SPECIFIC:
                signals[symbol] = await self._generate_specific_signal(symbol, market_data)
            else:  # COMPOSITE
                signals[symbol] = await self._generate_composite_signal(symbol, market_data)
        
        return signals
    
    async def _generate_base_signal(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Generate simple signal for BASE category"""
        
        # Simple momentum signal
        prices = market_data.get('prices', {})
        if symbol in prices:
            price = prices[symbol]
            # Simple signal based on price relative to 100 (simplified)
            return (price - 100.0) / 100.0
        
        return 0.0
    
    async def _generate_specific_signal(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Generate enhanced signal for SPECIFIC category"""
        
        base_signal = await self._generate_base_signal(symbol, market_data)
        
        # Add technical indicators
        rsi_signal = np.random.uniform(-0.1, 0.1)  # Simplified RSI
        macd_signal = np.random.uniform(-0.1, 0.1)  # Simplified MACD
        
        # Combine signals
        combined_signal = 0.5 * base_signal + 0.3 * rsi_signal + 0.2 * macd_signal
        
        return np.clip(combined_signal, -1.0, 1.0)
    
    async def _generate_composite_signal(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Generate sophisticated signal for COMPOSITE category"""
        
        specific_signal = await self._generate_specific_signal(symbol, market_data)
        
        # Add ensemble of additional indicators
        bollinger_signal = np.random.uniform(-0.1, 0.1)  # Simplified Bollinger Bands
        stochastic_signal = np.random.uniform(-0.1, 0.1)  # Simplified Stochastic
        volume_signal = np.random.uniform(-0.05, 0.05)    # Volume-based signal
        
        # Sophisticated combination
        ensemble_signal = (0.4 * specific_signal + 
                          0.2 * bollinger_signal + 
                          0.2 * stochastic_signal + 
                          0.2 * volume_signal)
        
        return np.clip(ensemble_signal, -1.0, 1.0)
    
    def _assess_signal_quality(self, signals: Dict[str, float]) -> float:
        """Assess quality of generated signals"""
        
        if not signals:
            return 0.0
        
        # Simple quality assessment based on signal strength and distribution
        signal_values = list(signals.values())
        avg_strength = np.mean([abs(s) for s in signal_values])
        signal_diversity = np.std(signal_values) if len(signal_values) > 1 else 0.0
        
        quality = min(1.0, avg_strength + 0.1 * signal_diversity)
        return quality

class CategoryAwareRiskAnalyzer(CategoryAwareComponent):
    """Category-aware risk analysis component"""
    
    async def initialize(self):
        """Initialize risk analyzer"""
        
        await self.adapt_to_category()
        
        # Category-specific risk parameters
        if self.category == TemplateCategory.BASE:
            self.risk_metrics = ['simple_volatility', 'max_position']
            self.risk_limits = {'max_position': 0.05, 'max_volatility': 0.02}
        elif self.category == TemplateCategory.SPECIFIC:
            self.risk_metrics = ['volatility', 'var', 'correlation']
            self.risk_limits = {'max_position': 0.08, 'max_volatility': 0.03, 'max_var': 0.02}
        else:  # COMPOSITE
            self.risk_metrics = ['volatility', 'var', 'cvar', 'correlation', 'tail_risk']
            self.risk_limits = {'max_position': 0.12, 'max_volatility': 0.04, 'max_var': 0.03}
        
        self.is_initialized = True
        self.logger.info(f"Risk analyzer initialized for {self.category.value}")
    
    async def process(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Analyze risk of position portfolio"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now()
        
        # Check cache
        cache_key = self._get_cache_key(positions)
        if self._should_use_cache(cache_key) and cache_key in self.cache:
            result = self.cache[cache_key]
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            await self.update_performance_metrics(execution_time, 1.0)
            return result
        
        # Perform risk analysis
        risk_analysis = await self._perform_category_risk_analysis(positions)
        
        # Cache result
        if self.cache and self._should_use_cache(cache_key):
            self.cache[cache_key] = risk_analysis
        
        # Update performance metrics
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        analysis_quality = self._assess_analysis_quality(risk_analysis)
        await self.update_performance_metrics(execution_time, analysis_quality)
        
        return risk_analysis
    
    async def _perform_category_risk_analysis(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Perform risk analysis based on category"""
        
        if self.category == TemplateCategory.BASE:
            return await self._basic_risk_analysis(positions)
        elif self.category == TemplateCategory.SPECIFIC:
            return await self._enhanced_risk_analysis(positions)
        else:  # COMPOSITE
            return await self._comprehensive_risk_analysis(positions)
    
    async def _basic_risk_analysis(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Basic risk analysis for BASE category"""
        
        if not positions:
            return {'total_risk': 0.0, 'max_position': 0.0, 'position_count': 0}
        
        total_exposure = sum(abs(pos) for pos in positions.values())
        max_position = max(abs(pos) for pos in positions.values())
        
        return {
            'total_risk': total_exposure,
            'max_position': max_position,
            'position_count': len(positions),
            'risk_level': 'low' if total_exposure < 0.1 else 'medium' if total_exposure < 0.3 else 'high'
        }
    
    async def _enhanced_risk_analysis(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Enhanced risk analysis for SPECIFIC category"""
        
        basic_analysis = await self._basic_risk_analysis(positions)
        
        if not positions:
            return basic_analysis
        
        # Add enhanced metrics
        position_values = list(positions.values())
        portfolio_volatility = np.std(position_values) if len(position_values) > 1 else 0.0
        concentration_risk = max(abs(pos) for pos in position_values) / sum(abs(pos) for pos in position_values)
        
        basic_analysis.update({
            'portfolio_volatility': portfolio_volatility,
            'concentration_risk': concentration_risk,
            'diversification_ratio': 1.0 / max(concentration_risk, 0.01),
            'var_95': np.percentile([abs(pos) for pos in position_values], 95) if position_values else 0.0
        })
        
        return basic_analysis
    
    async def _comprehensive_risk_analysis(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Comprehensive risk analysis for COMPOSITE category"""
        
        enhanced_analysis = await self._enhanced_risk_analysis(positions)
        
        if not positions:
            return enhanced_analysis
        
        # Add sophisticated metrics
        position_values = list(positions.values())
        
        # Tail risk analysis
        sorted_positions = sorted([abs(pos) for pos in position_values], reverse=True)
        tail_risk = sum(sorted_positions[:max(1, len(sorted_positions)//10)])  # Top 10% tail
        
        # Correlation analysis (simplified)
        correlation_risk = 0.5 if len(position_values) > 1 else 0.0  # Simplified correlation
        
        enhanced_analysis.update({
            'tail_risk': tail_risk,
            'correlation_risk': correlation_risk,
            'cvar_95': np.mean(sorted_positions[:max(1, len(sorted_positions)//20)]) if sorted_positions else 0.0,
            'risk_contribution': {symbol: abs(pos) / sum(abs(p) for p in position_values) 
                                for symbol, pos in positions.items()},
            'portfolio_beta': 1.0 + np.random.uniform(-0.2, 0.2)  # Simplified beta
        })
        
        return enhanced_analysis
    
    def _assess_analysis_quality(self, analysis: Dict[str, Any]) -> float:
        """Assess quality of risk analysis"""
        
        # Simple quality assessment based on completeness
        expected_metrics = len(self.risk_metrics)
        actual_metrics = len([k for k in analysis.keys() if k in self.risk_metrics])
        
        return actual_metrics / max(expected_metrics, 1)

class CategoryAwareCoreComponents:
    """
    Factory and manager for category-aware core components
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.component_instances = {}
        
    def create_signal_processor(self, template: BaseTemplate, 
                              config: Optional[ComponentAdaptationConfig] = None) -> CategoryAwareSignalProcessor:
        """Create category-aware signal processor"""
        
        if config is None:
            config = ComponentAdaptationConfig(target_category=template.metadata.category)
        
        return CategoryAwareSignalProcessor(template, config)
    
    def create_risk_analyzer(self, template: BaseTemplate,
                           config: Optional[ComponentAdaptationConfig] = None) -> CategoryAwareRiskAnalyzer:
        """Create category-aware risk analyzer"""
        
        if config is None:
            config = ComponentAdaptationConfig(target_category=template.metadata.category)
        
        return CategoryAwareRiskAnalyzer(template, config)
    
    async def get_component_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all components"""
        
        summary = {
            'total_components': len(self.component_instances),
            'category_distribution': {},
            'performance_metrics': {}
        }
        
        # Collect statistics
        for component_id, component in self.component_instances.items():
            category = component.category.value
            
            if category not in summary['category_distribution']:
                summary['category_distribution'][category] = 0
            summary['category_distribution'][category] += 1
            
            if hasattr(component, 'performance_metrics'):
                summary['performance_metrics'][component_id] = component.performance_metrics
        
        return summary
