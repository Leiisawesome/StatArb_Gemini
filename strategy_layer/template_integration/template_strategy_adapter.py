"""
Template Strategy Adapter
=========================

Adapter that converts hybrid templates into executable strategy objects,
bridging the template system with the existing strategy execution framework.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import uuid

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyType, StrategyStatus
from strategy_templates.base import (
    TemplateRegistry, TemplateInheritanceManager, StrategyAssembler,
    BaseTemplate, TemplateCategory, TemplateType as TemplateTypeEnum
)

logger = logging.getLogger(__name__)

@dataclass
class TemplateAdaptationResult:
    """Result of template adaptation process"""
    success: bool
    strategy_object: Optional[StrategyDefinition]
    template_id: str
    adaptation_time: datetime
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class TemplateStrategyAdapter:
    """
    Adapts hybrid templates into executable strategy objects compatible
    with the existing strategy execution framework.
    """
    
    def __init__(self, template_registry: TemplateRegistry,
                 inheritance_manager: TemplateInheritanceManager,
                 strategy_assembler: StrategyAssembler):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.template_registry = template_registry
        self.inheritance_manager = inheritance_manager
        self.strategy_assembler = strategy_assembler
        
        # Strategy type mapping between templates and legacy system
        self.template_to_strategy_type_mapping = {
            'momentum': StrategyType.MOMENTUM,
            'mean_reversion': StrategyType.MEAN_REVERSION,
            'pair_trading': StrategyType.PAIR_TRADING,
            'multi_factor': StrategyType.CUSTOM,
            'composite': StrategyType.CUSTOM
        }
        
        # Strategy class registry for template-based strategies
        self.template_strategy_classes: Dict[str, Type[StrategyDefinition]] = {}
        
        self.logger.info("TemplateStrategyAdapter initialized")
    
    def adapt_template_to_strategy(self, template_id: str, 
                                 custom_parameters: Optional[Dict[str, Any]] = None) -> TemplateAdaptationResult:
        """
        Adapt a template into an executable strategy object
        """
        try:
            adaptation_start = datetime.now()
            
            self.logger.info(f"Starting template adaptation for {template_id}")
            
            # Step 1: Resolve template with inheritance
            template = self.template_registry.get_template(template_id)
            if not template:
                return TemplateAdaptationResult(
                    success=False,
                    strategy_object=None,
                    template_id=template_id,
                    adaptation_time=adaptation_start,
                    errors=[f"Template {template_id} not found"]
                )
            
            # Step 2: Assemble complete strategy
            assembly_result = self.strategy_assembler.assemble_strategy(
                template_id, custom_parameters
            )
            
            if not assembly_result.success:
                return TemplateAdaptationResult(
                    success=False,
                    strategy_object=None,
                    template_id=template_id,
                    adaptation_time=adaptation_start,
                    errors=assembly_result.errors
                )
            
            assembled_template = assembly_result.assembled_strategy
            
            # Step 3: Convert to StrategyConfig
            strategy_config = self._convert_template_to_strategy_config(assembled_template)
            
            # Step 4: Create strategy object
            strategy_object = self._create_strategy_object(strategy_config, assembled_template)
            
            # Step 5: Enhance with template metadata
            strategy_object = self._enhance_with_template_metadata(strategy_object, assembled_template)
            
            adaptation_time = datetime.now()
            
            self.logger.info(f"Template {template_id} adapted successfully")
            
            return TemplateAdaptationResult(
                success=True,
                strategy_object=strategy_object,
                template_id=template_id,
                adaptation_time=adaptation_time,
                metadata={
                    'adaptation_duration_ms': (adaptation_time - adaptation_start).total_seconds() * 1000,
                    'template_category': assembled_template.metadata.category.value,
                    'template_type': assembled_template.metadata.template_type.value,
                    'inheritance_chain': self.inheritance_manager.get_inheritance_chain(template_id)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Template adaptation failed for {template_id}: {e}")
            return TemplateAdaptationResult(
                success=False,
                strategy_object=None,
                template_id=template_id,
                adaptation_time=datetime.now(),
                errors=[f"Adaptation failed: {e}"]
            )
    
    def _convert_template_to_strategy_config(self, template: BaseTemplate) -> StrategyConfig:
        """Convert template to legacy StrategyConfig format"""
        
        # Determine strategy type from template
        strategy_type = self._map_template_to_strategy_type(template)
        
        # Extract configuration sections
        signal_generation = template.components.get('signal_generation', {})
        risk_management = template.components.get('risk_management', {})
        entry_exit_logic = template.components.get('entry_exit_logic', {})
        execution = template.components.get('execution', {})
        portfolio_management = template.components.get('portfolio_management', {})
        
        # Create StrategyConfig
        strategy_config = StrategyConfig(
            strategy_id=template.metadata.template_id,
            strategy_type=strategy_type,
            name=template.metadata.name,
            version=template.metadata.version,
            description=template.metadata.description,
            status=self._map_template_status_to_strategy_status(template.metadata.status),
            created_date=template.metadata.created_at,
            updated_date=template.metadata.updated_at,
            metadata={
                'template_origin': True,
                'template_category': template.metadata.category.value,
                'template_type': template.metadata.template_type.value,
                'parent_templates': template.metadata.parent_templates,
                'tags': template.metadata.tags
            },
            signal_generation=signal_generation,
            risk_management=risk_management,
            entry_exit_logic=entry_exit_logic,
            execution=execution,
            portfolio_management=portfolio_management,
            parameters=template.parameters
        )
        
        return strategy_config
    
    def _map_template_to_strategy_type(self, template: BaseTemplate) -> StrategyType:
        """Map template to legacy strategy type"""
        
        # Look for strategy type hints in template
        template_name = template.metadata.name.lower()
        template_tags = [tag.lower() for tag in template.metadata.tags]
        
        # Check template tags first
        for tag in template_tags:
            if tag in self.template_to_strategy_type_mapping:
                return self.template_to_strategy_type_mapping[tag]
        
        # Check template name
        for template_type_key in self.template_to_strategy_type_mapping:
            if template_type_key in template_name:
                return self.template_to_strategy_type_mapping[template_type_key]
        
        # Default to custom for complex templates
        if template.metadata.category == TemplateCategory.COMPOSITE:
            return StrategyType.CUSTOM
        
        # Fallback based on template type
        if template.metadata.template_type == TemplateTypeEnum.COMPLETE_STRATEGY:
            return StrategyType.CUSTOM
        
        return StrategyType.MOMENTUM  # Default fallback
    
    def _map_template_status_to_strategy_status(self, template_status) -> StrategyStatus:
        """Map template status to strategy status"""
        status_mapping = {
            'draft': StrategyStatus.DRAFT,
            'validated': StrategyStatus.TESTING,
            'production': StrategyStatus.ACTIVE,
            'deprecated': StrategyStatus.ARCHIVED
        }
        
        template_status_str = template_status.value if hasattr(template_status, 'value') else str(template_status)
        return status_mapping.get(template_status_str.lower(), StrategyStatus.DRAFT)
    
    def _create_strategy_object(self, strategy_config: StrategyConfig, 
                              template: BaseTemplate) -> StrategyDefinition:
        """Create strategy object from config and template"""
        
        # Check if we have a template-specific strategy class
        template_type = template.metadata.template_type.value
        strategy_class = self.template_strategy_classes.get(template_type)
        
        if strategy_class:
            return strategy_class(strategy_config)
        
        # Create adaptive strategy object that can handle any template
        return TemplateAdaptiveStrategy(strategy_config, template)
    
    def _enhance_with_template_metadata(self, strategy_object: StrategyDefinition, 
                                      template: BaseTemplate) -> StrategyDefinition:
        """Enhance strategy object with template metadata"""
        
        # Add template-specific methods and properties
        strategy_object._template = template
        strategy_object._template_metadata = template.metadata
        strategy_object._template_components = template.components
        strategy_object._template_parameters = template.parameters
        
        # Add template-aware methods
        def get_template():
            return template
        
        def get_template_metadata():
            return template.metadata
        
        def get_inheritance_chain():
            return self.inheritance_manager.get_inheritance_chain(template.metadata.template_id)
        
        # Bind methods to strategy object
        strategy_object.get_template = get_template
        strategy_object.get_template_metadata = get_template_metadata
        strategy_object.get_inheritance_chain = get_inheritance_chain
        
        return strategy_object
    
    def register_template_strategy_class(self, template_type: str, 
                                       strategy_class: Type[StrategyDefinition]):
        """Register a strategy class for a specific template type"""
        self.template_strategy_classes[template_type] = strategy_class
        self.logger.info(f"Registered template strategy class for {template_type}")
    
    def bulk_adapt_templates(self, template_ids: List[str]) -> Dict[str, TemplateAdaptationResult]:
        """Adapt multiple templates in bulk"""
        results = {}
        
        for template_id in template_ids:
            results[template_id] = self.adapt_template_to_strategy(template_id)
        
        return results
    
    def get_adaptation_statistics(self) -> Dict[str, Any]:
        """Get statistics about template adaptations"""
        return {
            'registered_template_classes': len(self.template_strategy_classes),
            'template_to_strategy_mappings': len(self.template_to_strategy_type_mapping),
            'available_templates': self.template_registry.get_registry_stats()['total_templates']
        }


class TemplateAdaptiveStrategy(StrategyDefinition):
    """
    Adaptive strategy that can execute any template-based strategy
    by dynamically interpreting template components.
    """
    
    def __init__(self, config: StrategyConfig, template: BaseTemplate):
        super().__init__(config)
        self.template = template
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{template.metadata.template_id}")
        self._setup_template_execution()
    
    def _setup_template_execution(self):
        """Setup execution components based on template"""
        self.signal_components = self.template.components.get('signal_generation', {})
        self.risk_components = self.template.components.get('risk_management', {})
        self.execution_components = self.template.components.get('execution', {})
        self.portfolio_components = self.template.components.get('portfolio_management', {})
    
    def generate_signals(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """Generate signals using template-defined logic"""
        try:
            signals = {}
            
            # Use template signal generation configuration
            signal_config = self.signal_components
            
            if not signal_config:
                self.logger.warning("No signal generation configuration in template")
                return {}
            
            # Extract signal type and parameters
            signal_type = signal_config.get('type', 'momentum_signals')
            
            # Basic signal generation based on template configuration
            if 'momentum' in signal_type.lower():
                signals = self._generate_momentum_signals(market_data, signal_config)
            elif 'mean_reversion' in signal_type.lower():
                signals = self._generate_mean_reversion_signals(market_data, signal_config)
            elif 'enhanced' in signal_type.lower():
                signals = self._generate_enhanced_signals(market_data, signal_config)
            else:
                # Default signal generation
                signals = self._generate_default_signals(market_data, signal_config)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Signal generation failed: {e}")
            return {}
    
    def calculate_position_sizes(self, signals: Dict[str, float], 
                               market_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate position sizes using template risk management"""
        try:
            position_sizes = {}
            
            # Get position sizing parameters from template
            max_position = self.template.parameters.get('max_positions', 50)
            position_size = self.template.parameters.get('position_size', 0.02)
            
            # Calculate position sizes based on signals
            for symbol, signal in signals.items():
                if abs(signal) > 0.1:  # Minimum signal threshold
                    # Scale position size by signal strength
                    scaled_size = position_size * abs(signal)
                    position_sizes[symbol] = min(scaled_size, position_size * 2)  # Cap at 2x base size
            
            return position_sizes
            
        except Exception as e:
            self.logger.error(f"Position sizing failed: {e}")
            return {}
    
    def validate_risk(self, positions: Dict[str, float], 
                     market_data: Dict[str, Any]) -> bool:
        """Validate risk using template risk parameters"""
        try:
            # Get risk parameters from template
            max_positions = self.template.parameters.get('max_positions', 50)
            max_single_position = self.template.parameters.get('max_single_position', 0.05)
            
            # Check position count
            if len(positions) > max_positions:
                self.logger.warning(f"Position count {len(positions)} exceeds maximum {max_positions}")
                return False
            
            # Check individual position sizes
            for symbol, size in positions.items():
                if abs(size) > max_single_position:
                    self.logger.warning(f"Position size {size} for {symbol} exceeds maximum {max_single_position}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Risk validation failed: {e}")
            return False
    
    def should_enter_position(self, symbol: str, signal: float, 
                            market_data: Dict[str, Any]) -> bool:
        """Determine if should enter position using template logic"""
        try:
            # Get entry thresholds from template
            entry_threshold = self.template.parameters.get('momentum_threshold', 0.02)
            
            return abs(signal) > entry_threshold
            
        except Exception as e:
            self.logger.error(f"Entry decision failed: {e}")
            return False
    
    def should_exit_position(self, symbol: str, position: float, 
                           market_data: Dict[str, Any]) -> bool:
        """Determine if should exit position using template logic"""
        try:
            # Get exit parameters from template
            stop_loss = self.template.parameters.get('stop_loss', 0.05)
            take_profit = self.template.parameters.get('take_profit', 0.10)
            
            # Basic exit logic (would be enhanced with real market data)
            # For now, use placeholder logic
            return False  # Placeholder
            
        except Exception as e:
            self.logger.error(f"Exit decision failed: {e}")
            return False
    
    def _generate_momentum_signals(self, market_data: Dict[str, Any], 
                                 signal_config: Dict[str, Any]) -> Dict[str, float]:
        """Generate momentum-based signals"""
        # Placeholder momentum signal generation
        signals = {}
        
        # Use template parameters
        lookback = self.template.parameters.get('lookback_period', 20)
        threshold = self.template.parameters.get('momentum_threshold', 0.02)
        
        # Simulate momentum signals (in real implementation, would use actual market data)
        symbols = market_data.get('symbols', ['AAPL', 'GOOGL', 'MSFT'])
        
        for symbol in symbols:
            # Placeholder signal calculation
            signal_strength = 0.5  # Would be calculated from real data
            if signal_strength > threshold:
                signals[symbol] = signal_strength
        
        return signals
    
    def _generate_mean_reversion_signals(self, market_data: Dict[str, Any], 
                                       signal_config: Dict[str, Any]) -> Dict[str, float]:
        """Generate mean reversion signals"""
        # Placeholder mean reversion signal generation
        return {}
    
    def _generate_enhanced_signals(self, market_data: Dict[str, Any], 
                                 signal_config: Dict[str, Any]) -> Dict[str, float]:
        """Generate enhanced signals using multiple factors"""
        # Placeholder enhanced signal generation
        return {}
    
    def _generate_default_signals(self, market_data: Dict[str, Any], 
                                signal_config: Dict[str, Any]) -> Dict[str, float]:
        """Generate default signals"""
        # Basic signal generation fallback
        return {'DEFAULT': 0.5}
