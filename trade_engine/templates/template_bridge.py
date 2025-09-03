"""
Template-Strategy Bridge
=======================

Professional bridge system that converts strategy templates (WHAT) to
executable strategy implementations (HOW). This maintains clean separation
between strategy definition and implementation.

Author: Professional Trading System Architecture
Version: 1.0.0
"""

from typing import Dict, List, Any, Optional, Type
import pandas as pd
import logging
from dataclasses import dataclass
from datetime import datetime

# Updated imports after removing obsolete trade_engine.interfaces
from core_structure.interfaces import StrategyInterface
from ..templates.base_template import BaseTemplate, template_registry, SignalRule, SignalCondition
from ..templates.base_template import TemplateValidationError


@dataclass
class RawSignal:
    """Raw signal data from strategy calculations (local definition)"""
    symbol: str
    value: float
    confidence: float
    signal_metadata: Dict[str, Any]
    timestamp: pd.Timestamp


@dataclass
class TemplateConfiguration:
    """Configuration for template-based strategy."""
    template_id: str
    parameters: Dict[str, Any]
    strategy_instance_id: str
    metadata: Optional[Dict[str, Any]] = None


class TemplateStrategyBridge(StrategyInterface):
    """
    Bridge that converts templates to executable strategies.
    
    This class implements the StrategyInterface while delegating signal
    generation logic to template definitions. It handles the conversion
    from template rules to actual signal calculations.
    """
    
    def __init__(self, template_config: TemplateConfiguration):
        """
        Initialize template-strategy bridge.
        
        Args:
            template_config: Template configuration including ID and parameters
        """
        self.template_config = template_config
        self.logger = logging.getLogger(__name__)
        
        # Load template from registry
        self.template = template_registry.get_template(template_config.template_id)
        if not self.template:
            raise TemplateValidationError(f"Template {template_config.template_id} not found in registry")
        
        # Validate parameters against template bounds
        self.template.validate_parameters(template_config.parameters)
        
        # Resolve template configuration with parameters
        self.resolved_config = self.template.resolve_parameter_references(template_config.parameters)
        
        # Initialize indicator calculators
        self._indicator_calculators = self._initialize_indicator_calculators()
        
        self.logger.info(f"TemplateStrategyBridge initialized with template {template_config.template_id}")
    
    def calculate_signals(self, market_data: pd.DataFrame) -> List[RawSignal]:
        """
        Calculate signals based on template definitions.
        
        Args:
            market_data: Market data DataFrame
            
        Returns:
            List of raw signals generated from template rules
        """
        try:
            if market_data.empty:
                self.logger.warning("Empty market data provided")
                return []
            
            # Calculate required indicators
            indicators = self._calculate_indicators(market_data)
            
            # Process signal rules from template
            raw_signals = []
            
            # Group market data by symbol for processing
            symbols = market_data['symbol'].unique() if 'symbol' in market_data.columns else ['DEFAULT']
            
            for symbol in symbols:
                symbol_data = market_data[market_data['symbol'] == symbol] if 'symbol' in market_data.columns else market_data
                symbol_indicators = self._extract_symbol_indicators(indicators, symbol, symbol_data)
                
                # Generate signals for this symbol
                symbol_signals = self._generate_symbol_signals(symbol, symbol_data, symbol_indicators)
                raw_signals.extend(symbol_signals)
            
            self.logger.debug(f"Generated {len(raw_signals)} raw signals from template")
            return raw_signals
            
        except Exception as e:
            self.logger.error(f"Signal calculation failed: {e}")
            return []
    
    def _calculate_indicators(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all required indicators for the template."""
        indicators = {}
        
        try:
            # Basic price indicators
            if 'close' in market_data.columns:
                indicators['close'] = market_data['close']
            
            if 'volume' in market_data.columns:
                indicators['volume'] = market_data['volume']
            
            # Calculate momentum score
            indicators['momentum_score'] = self._calculate_momentum_score(market_data)
            
            # Calculate volume ratio
            indicators['volume_ratio'] = self._calculate_volume_ratio(market_data)
            
            # Calculate trend strength
            indicators['trend_strength'] = self._calculate_trend_strength(market_data)
            
            # Calculate volatility percentile
            indicators['volatility_percentile'] = self._calculate_volatility_percentile(market_data)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Indicator calculation failed: {e}")
            return {}
    
    def _calculate_momentum_score(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate momentum score using template parameters."""
        if 'close' not in market_data.columns:
            return pd.Series(0.0, index=market_data.index)
        
        lookback = self.template_config.parameters.get('lookback_period', 20)
        
        # Calculate price momentum (rate of change)
        close_prices = market_data['close']
        momentum = close_prices.pct_change(periods=lookback)
        
        # Apply volatility adjustment if specified
        volatility_adj = self.template_config.parameters.get('volatility_adjustment', 1.0)
        if volatility_adj != 1.0:
            volatility = close_prices.rolling(window=lookback).std()
            momentum = momentum * (volatility_adj / (volatility + 1e-8))
        
        return momentum.fillna(0.0)
    
    def _calculate_volume_ratio(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate volume ratio using template parameters."""
        if 'volume' not in market_data.columns:
            return pd.Series(1.0, index=market_data.index)
        
        volume_lookback = self.template_config.parameters.get('volume_lookback', 10)
        
        volume = market_data['volume']
        avg_volume = volume.rolling(window=volume_lookback).mean()
        volume_ratio = volume / (avg_volume + 1e-8)
        
        return volume_ratio.fillna(1.0)
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate trend strength indicator."""
        if 'close' not in market_data.columns:
            return pd.Series(0.5, index=market_data.index)
        
        lookback = self.template_config.parameters.get('lookback_period', 20)
        
        close_prices = market_data['close']
        
        # Calculate trend using linear regression slope
        def calculate_trend_slope(prices):
            if len(prices) < 2:
                return 0.0
            x = range(len(prices))
            y = prices.values
            n = len(x)
            
            if n == 0:
                return 0.0
            
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            
            denominator = n * sum_x2 - sum_x ** 2
            if abs(denominator) < 1e-8:
                return 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            return slope
        
        trend_slopes = close_prices.rolling(window=lookback).apply(calculate_trend_slope)
        
        # Normalize to 0-1 range
        trend_strength = (trend_slopes - trend_slopes.min()) / (trend_slopes.max() - trend_slopes.min() + 1e-8)
        
        return trend_strength.fillna(0.5)
    
    def _calculate_volatility_percentile(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate volatility percentile."""
        if 'close' not in market_data.columns:
            return pd.Series(0.5, index=market_data.index)
        
        lookback = self.template_config.parameters.get('lookback_period', 20)
        
        close_prices = market_data['close']
        returns = close_prices.pct_change()
        volatility = returns.rolling(window=lookback).std()
        
        # Calculate percentile ranking
        volatility_percentile = volatility.rolling(window=lookback * 3).rank(pct=True)
        
        return volatility_percentile.fillna(0.5)
    
    def _extract_symbol_indicators(self, indicators: Dict[str, Any], symbol: str, symbol_data: pd.DataFrame) -> Dict[str, float]:
        """Extract current indicator values for a specific symbol."""
        symbol_indicators = {}
        
        for indicator_name, indicator_values in indicators.items():
            if isinstance(indicator_values, pd.Series) and not indicator_values.empty:
                # Get the latest value for this symbol
                symbol_indicators[indicator_name] = float(indicator_values.iloc[-1])
            else:
                symbol_indicators[indicator_name] = 0.0
        
        return symbol_indicators
    
    def _generate_symbol_signals(self, symbol: str, symbol_data: pd.DataFrame, indicators: Dict[str, float]) -> List[RawSignal]:
        """Generate signals for a specific symbol using template rules."""
        signals = []
        
        try:
            # Process each signal rule from the resolved template configuration
            for rule_dict in self.resolved_config['signal_rules']:
                # Convert back to SignalRule object if needed
                if isinstance(rule_dict, dict):
                    rule = SignalRule(**rule_dict)
                else:
                    rule = rule_dict
                
                # Evaluate signal rule
                signal_value, confidence = self._evaluate_signal_rule(rule, indicators)
                
                if abs(signal_value) > 0.001:  # Only create signal if significant
                    raw_signal = RawSignal(
                        symbol=symbol,
                        value=signal_value,
                        confidence=confidence,
                        signal_metadata={
                            'rule_id': rule.rule_id,
                            'rule_type': rule.metadata.get('signal_type', 'unknown') if rule.metadata else 'unknown',
                            'template_id': self.template_config.template_id,
                            'strategy_instance_id': self.template_config.strategy_instance_id,
                            'indicators_used': list(indicators.keys()),
                            'rule_metadata': rule.metadata
                        },
                        timestamp=pd.Timestamp.now()
                    )
                    signals.append(raw_signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Signal generation failed for {symbol}: {e}")
            return []
    
    def _evaluate_signal_rule(self, rule: SignalRule, indicators: Dict[str, float]) -> tuple[float, float]:
        """
        Evaluate a signal rule against current indicators.
        
        Returns:
            Tuple of (signal_value, confidence)
        """
        try:
            # Get indicator value
            indicator_value = indicators.get(rule.indicator, 0.0)
            threshold = float(rule.threshold)
            
            # Evaluate condition
            signal_triggered = self._evaluate_condition(rule.condition, indicator_value, threshold)
            
            if signal_triggered:
                # Calculate signal strength based on how much the condition is exceeded
                signal_strength = self._calculate_signal_strength(rule.condition, indicator_value, threshold)
                signal_value = signal_strength * rule.signal_strength
                
                # Handle negative momentum for short signals
                if rule.metadata and rule.metadata.get('threshold_sign') == 'negative':
                    signal_value = -abs(signal_value)
                
                confidence = min(0.95, abs(signal_strength) * rule.confidence_multiplier)
                
                return signal_value, confidence
            
            return 0.0, 0.0
            
        except Exception as e:
            self.logger.error(f"Rule evaluation failed for {rule.rule_id}: {e}")
            return 0.0, 0.0
    
    def _evaluate_condition(self, condition: SignalCondition, value: float, threshold: float) -> bool:
        """Evaluate a signal condition."""
        if condition == SignalCondition.GREATER_THAN:
            return value > threshold
        elif condition == SignalCondition.LESS_THAN:
            return value < threshold
        elif condition == SignalCondition.EQUAL_TO:
            return abs(value - threshold) < 1e-6
        # Add more conditions as needed
        return False
    
    def _calculate_signal_strength(self, condition: SignalCondition, value: float, threshold: float) -> float:
        """Calculate signal strength based on how much the condition is exceeded."""
        if condition == SignalCondition.GREATER_THAN:
            if value > threshold:
                return min(1.0, (value - threshold) / (threshold + 1e-8))
        elif condition == SignalCondition.LESS_THAN:
            if value < threshold:
                return min(1.0, (threshold - value) / (threshold + 1e-8))
        
        return 0.0
    
    def _initialize_indicator_calculators(self) -> Dict[str, Any]:
        """Initialize indicator calculation functions."""
        return {
            'momentum_score': self._calculate_momentum_score,
            'volume_ratio': self._calculate_volume_ratio,
            'trend_strength': self._calculate_trend_strength,
            'volatility_percentile': self._calculate_volatility_percentile
        }
    
    def get_strategy_name(self) -> str:
        """Return the strategy name."""
        return f"{self.template.name}_{self.template_config.strategy_instance_id}"
    
    def get_required_indicators(self) -> List[str]:
        """Return required indicators from template."""
        return self.template.get_required_indicators()
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters using template bounds."""
        return self.template.validate_parameters(parameters)
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get template information."""
        return {
            'template_info': self.template.get_template_info(),
            'resolved_config': self.resolved_config,
            'strategy_instance_id': self.template_config.strategy_instance_id
        }


class TemplateStrategyFactory:
    """
    Factory for creating template-based strategies.
    
    Provides a centralized way to create strategy instances from templates
    with proper validation and configuration management.
    """
    
    def __init__(self):
        """Initialize template strategy factory."""
        self.logger = logging.getLogger(__name__)
        self._created_strategies: Dict[str, TemplateStrategyBridge] = {}
    
    def create_strategy(
        self,
        template_id: str,
        parameters: Dict[str, Any],
        strategy_instance_id: Optional[str] = None
    ) -> TemplateStrategyBridge:
        """
        Create a strategy instance from a template.
        
        Args:
            template_id: ID of the template to use
            parameters: Strategy parameters
            strategy_instance_id: Unique ID for this strategy instance
            
        Returns:
            TemplateStrategyBridge instance
        """
        if strategy_instance_id is None:
            strategy_instance_id = f"{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate template exists
        template = template_registry.get_template(template_id)
        if not template:
            raise TemplateValidationError(f"Template {template_id} not found")
        
        # Create template configuration
        template_config = TemplateConfiguration(
            template_id=template_id,
            parameters=parameters,
            strategy_instance_id=strategy_instance_id
        )
        
        # Create strategy bridge
        strategy = TemplateStrategyBridge(template_config)
        
        # Cache strategy instance
        self._created_strategies[strategy_instance_id] = strategy
        
        self.logger.info(f"Created strategy instance {strategy_instance_id} from template {template_id}")
        return strategy
    
    def get_strategy(self, strategy_instance_id: str) -> Optional[TemplateStrategyBridge]:
        """Get a previously created strategy instance."""
        return self._created_strategies.get(strategy_instance_id)
    
    def list_created_strategies(self) -> List[str]:
        """List all created strategy instance IDs."""
        return list(self._created_strategies.keys())
    
    def get_factory_status(self) -> Dict[str, Any]:
        """Get factory status information."""
        return {
            'created_strategies_count': len(self._created_strategies),
            'strategy_instance_ids': list(self._created_strategies.keys()),
            'available_templates': template_registry.list_templates()
        }


# Global factory instance
template_strategy_factory = TemplateStrategyFactory()
