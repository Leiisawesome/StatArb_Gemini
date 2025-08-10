"""
Strategy Builder

Builder system for assembling strategies from building blocks and components.

Author: Pro Quant Desk Trader
"""

import logging
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

from strategy_layer.base import StrategyDefinition, StrategyConfig, StrategyError
from .strategy_factory import StrategyFactory


class StrategyBuilder:
    """Builder for assembling strategies from building blocks"""
    
    def __init__(self, factory: Optional[StrategyFactory] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.factory = factory or StrategyFactory()
        self._building_blocks = {}
        self._composition_rules = {}
        self._register_default_building_blocks()
    
    def add_building_block(self, block_name: str, block_class: Any):
        """
        Add a building block to the builder
        
        Args:
            block_name: Name of the building block
            block_class: Building block class
        """
        self._building_blocks[block_name] = block_class
        self.logger.info(f"Added building block: {block_name}")
    
    def add_composition_rule(self, rule_name: str, rule_func: callable):
        """
        Add a composition rule
        
        Args:
            rule_name: Name of the composition rule
            rule_func: Composition rule function
        """
        self._composition_rules[rule_name] = rule_func
        self.logger.info(f"Added composition rule: {rule_name}")
    
    def build_strategy(self, strategy_data: Dict[str, Any]) -> StrategyDefinition:
        """
        Build a strategy from data using building blocks
        
        Args:
            strategy_data: Strategy data
            
        Returns:
            Built strategy object
            
        Raises:
            StrategyError: If building fails
        """
        try:
            self.logger.info(f"Building strategy: {strategy_data.get('strategy_name', 'Unknown')}")
            
            # Validate strategy data
            self.factory.validate_strategy_data(strategy_data)
            
            # Assemble building blocks
            assembled_data = self._assemble_building_blocks(strategy_data)
            
            # Create strategy using factory
            strategy = self.factory.create_strategy(assembled_data)
            
            self.logger.info(f"Successfully built strategy: {strategy_data.get('strategy_name', 'Unknown')}")
            return strategy
            
        except Exception as e:
            error_msg = f"Failed to build strategy: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def build_strategy_from_template(self, template_name: str, **kwargs) -> StrategyDefinition:
        """
        Build a strategy from template using building blocks
        
        Args:
            template_name: Template name
            **kwargs: Template parameters
            
        Returns:
            Built strategy object
            
        Raises:
            StrategyError: If building fails
        """
        try:
            self.logger.info(f"Building strategy from template: {template_name}")
            
            # Get template
            template = self.factory.get_template(template_name)
            if not template:
                raise StrategyError(f"Template not found: {template_name}")
            
            # Merge template with parameters
            strategy_data = template.copy()
            strategy_data.update(kwargs)
            
            # Build strategy
            return self.build_strategy(strategy_data)
            
        except Exception as e:
            error_msg = f"Failed to build strategy from template {template_name}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def build_strategy_from_file(self, file_path: str) -> StrategyDefinition:
        """
        Build a strategy from file using building blocks
        
        Args:
            file_path: Path to strategy file
            
        Returns:
            Built strategy object
            
        Raises:
            StrategyError: If building fails
        """
        try:
            self.logger.info(f"Building strategy from file: {file_path}")
            
            # Parse and build strategy
            strategy = self.factory.create_strategy_from_file(file_path)
            
            # Apply building block assembly
            strategy_data = strategy.to_dict()
            assembled_data = self._assemble_building_blocks(strategy_data)
            
            # Recreate strategy with assembled data
            return self.factory.create_strategy(assembled_data)
            
        except Exception as e:
            error_msg = f"Failed to build strategy from file {file_path}: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def _assemble_building_blocks(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assemble building blocks for strategy data
        
        Args:
            strategy_data: Strategy data
            
        Returns:
            Assembled strategy data
        """
        try:
            assembled_data = strategy_data.copy()
            
            # Assemble signal generation building blocks
            if 'signal_generation' in strategy_data:
                assembled_data['signal_generation'] = self._assemble_signal_generation(
                    strategy_data['signal_generation']
                )
            
            # Assemble risk management building blocks
            if 'risk_management' in strategy_data:
                assembled_data['risk_management'] = self._assemble_risk_management(
                    strategy_data['risk_management']
                )
            
            # Assemble entry/exit logic building blocks
            if 'entry_exit_logic' in strategy_data:
                assembled_data['entry_exit_logic'] = self._assemble_entry_exit_logic(
                    strategy_data['entry_exit_logic']
                )
            
            # Assemble execution building blocks
            if 'execution' in strategy_data:
                assembled_data['execution'] = self._assemble_execution(
                    strategy_data['execution']
                )
            
            # Assemble portfolio management building blocks
            if 'portfolio_management' in strategy_data:
                assembled_data['portfolio_management'] = self._assemble_portfolio_management(
                    strategy_data['portfolio_management']
                )
            
            return assembled_data
            
        except Exception as e:
            error_msg = f"Failed to assemble building blocks: {e}"
            self.logger.error(error_msg)
            raise StrategyError(error_msg) from e
    
    def _assemble_signal_generation(self, signal_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble signal generation building blocks"""
        assembled_config = signal_config.copy()
        
        # Process indicators
        if 'indicators' in signal_config:
            indicators = signal_config['indicators']
            assembled_indicators = []
            
            for indicator in indicators:
                indicator_type = indicator.get('type')
                if indicator_type in self._building_blocks:
                    # Apply building block processing
                    block_class = self._building_blocks[indicator_type]
                    processed_indicator = self._process_indicator(indicator, block_class)
                    assembled_indicators.append(processed_indicator)
                else:
                    # Use indicator as-is
                    assembled_indicators.append(indicator)
            
            assembled_config['indicators'] = assembled_indicators
        
        return assembled_config
    
    def _assemble_risk_management(self, risk_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble risk management building blocks"""
        assembled_config = risk_config.copy()
        
        # Process position sizing
        if 'position_sizing' in risk_config:
            position_config = risk_config['position_sizing']
            method = position_config.get('method')
            
            if method in self._building_blocks:
                block_class = self._building_blocks[method]
                assembled_config['position_sizing'] = self._process_position_sizing(
                    position_config, block_class
                )
        
        return assembled_config
    
    def _assemble_entry_exit_logic(self, logic_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble entry/exit logic building blocks"""
        assembled_config = logic_config.copy()
        
        # Process entry conditions
        if 'entry_conditions' in logic_config:
            entry_conditions = logic_config['entry_conditions']
            assembled_conditions = []
            
            for condition in entry_conditions:
                condition_type = condition.get('condition')
                if condition_type in self._building_blocks:
                    block_class = self._building_blocks[condition_type]
                    processed_condition = self._process_condition(condition, block_class)
                    assembled_conditions.append(processed_condition)
                else:
                    assembled_conditions.append(condition)
            
            assembled_config['entry_conditions'] = assembled_conditions
        
        return assembled_config
    
    def _assemble_execution(self, execution_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble execution building blocks"""
        assembled_config = execution_config.copy()
        
        # Process execution algorithm
        if 'execution_algorithm' in execution_config:
            algorithm = execution_config['execution_algorithm']
            if algorithm in self._building_blocks:
                block_class = self._building_blocks[algorithm]
                assembled_config['execution_algorithm'] = self._process_execution_algorithm(
                    execution_config, block_class
                )
        
        return assembled_config
    
    def _assemble_portfolio_management(self, portfolio_config: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble portfolio management building blocks"""
        assembled_config = portfolio_config.copy()
        
        # Process rebalancing
        if 'rebalancing' in portfolio_config:
            rebalancing_config = portfolio_config['rebalancing']
            method = rebalancing_config.get('method')
            
            if method in self._building_blocks:
                block_class = self._building_blocks[method]
                assembled_config['rebalancing'] = self._process_rebalancing(
                    rebalancing_config, block_class
                )
        
        return assembled_config
    
    def _process_indicator(self, indicator: Dict[str, Any], block_class: Any) -> Dict[str, Any]:
        """Process indicator using building block"""
        # This would apply building block logic to the indicator
        # For now, return as-is
        return indicator
    
    def _process_position_sizing(self, position_config: Dict[str, Any], block_class: Any) -> Dict[str, Any]:
        """Process position sizing using building block"""
        # This would apply building block logic to position sizing
        # For now, return as-is
        return position_config
    
    def _process_condition(self, condition: Dict[str, Any], block_class: Any) -> Dict[str, Any]:
        """Process condition using building block"""
        # This would apply building block logic to the condition
        # For now, return as-is
        return condition
    
    def _process_execution_algorithm(self, execution_config: Dict[str, Any], block_class: Any) -> Dict[str, Any]:
        """Process execution algorithm using building block"""
        # This would apply building block logic to execution
        # For now, return as-is
        return execution_config
    
    def _process_rebalancing(self, rebalancing_config: Dict[str, Any], block_class: Any) -> Dict[str, Any]:
        """Process rebalancing using building block"""
        # This would apply building block logic to rebalancing
        # For now, return as-is
        return rebalancing_config
    
    def _register_default_building_blocks(self):
        """Register default building blocks"""
        self.logger.info("Registering default building blocks")
        
        # This will be populated when we implement the building blocks
        # For now, we'll create placeholder registrations
        
        # Signal generation building blocks
        # self.add_building_block('rsi', RSIIndicator)
        # self.add_building_block('macd', MACDIndicator)
        # self.add_building_block('zscore', ZScoreIndicator)
        
        # Risk management building blocks
        # self.add_building_block('fixed', FixedPositionSizer)
        # self.add_building_block('kelly', KellyPositionSizer)
        # self.add_building_block('volatility_adjusted', VolatilityAdjustedPositionSizer)
        
        # Entry/exit logic building blocks
        # self.add_building_block('signal_threshold', SignalThresholdCondition)
        # self.add_building_block('time_based', TimeBasedCondition)
        
        # Execution building blocks
        # self.add_building_block('twap', TWAPExecution)
        # self.add_building_block('vwap', VWAPExecution)
        
        # Portfolio management building blocks
        # self.add_building_block('equal_weight', EqualWeightRebalancing)
        # self.add_building_block('risk_parity', RiskParityRebalancing)
        
        self.logger.info("Default building blocks registered")
    
    def get_available_building_blocks(self) -> List[str]:
        """
        Get list of available building blocks
        
        Returns:
            List of building block names
        """
        return list(self._building_blocks.keys())
    
    def get_available_composition_rules(self) -> List[str]:
        """
        Get list of available composition rules
        
        Returns:
            List of composition rule names
        """
        return list(self._composition_rules.keys())
    
    def get_building_block(self, block_name: str) -> Optional[Any]:
        """
        Get building block by name
        
        Args:
            block_name: Name of the building block
            
        Returns:
            Building block class or None if not found
        """
        return self._building_blocks.get(block_name)
    
    def get_composition_rule(self, rule_name: str) -> Optional[callable]:
        """
        Get composition rule by name
        
        Args:
            rule_name: Name of the composition rule
            
        Returns:
            Composition rule function or None if not found
        """
        return self._composition_rules.get(rule_name)
