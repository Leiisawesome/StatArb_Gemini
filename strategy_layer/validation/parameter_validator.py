"""
Parameter Validator

Parameter validation and sensitivity analysis for strategies.

Author: Pro Quant Desk Trader
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .strategy_validator import (
    StrategyValidator,
    ValidationConfig,
    ValidationResult
)
from .backtesting_validator import BacktestingValidator
from strategy_layer.base import StrategyError, StrategyDefinition


@dataclass
class ParameterSensitivity:
    """Parameter sensitivity analysis result"""
    parameter_name: str
    base_value: float
    test_values: List[float]
    test_results: List[float]
    sensitivity_score: float
    optimal_value: float
    optimal_result: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'parameter_name': self.parameter_name,
            'base_value': self.base_value,
            'test_values': self.test_values,
            'test_results': self.test_results,
            'sensitivity_score': self.sensitivity_score,
            'optimal_value': self.optimal_value,
            'optimal_result': self.optimal_result
        }


@dataclass
class ParameterValidationResult:
    """Result of parameter validation"""
    # Strategy information
    strategy_id: str
    strategy_name: str
    
    # Parameter analysis
    parameter_sensitivities: List[ParameterSensitivity]
    parameter_importance: Dict[str, float]
    parameter_correlations: Dict[str, Dict[str, float]]
    
    # Validation metrics
    parameter_stability: float
    optimal_parameters: Dict[str, float]
    parameter_robustness: float
    
    # Detailed data
    validation_date: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'parameter_sensitivities': [ps.to_dict() for ps in self.parameter_sensitivities],
            'parameter_importance': self.parameter_importance,
            'parameter_correlations': self.parameter_correlations,
            'parameter_stability': self.parameter_stability,
            'optimal_parameters': self.optimal_parameters,
            'parameter_robustness': self.parameter_robustness,
            'validation_date': self.validation_date.isoformat() if self.validation_date else None
        }


class ParameterValidator(StrategyValidator):
    """Parameter validator for strategy validation"""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.sensitivities: List[ParameterSensitivity] = []
        self.parameter_results: Dict[str, List[float]] = {}
    
    def validate_strategy(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """Validate strategy parameters"""
        try:
            self.logger.info(f"Starting parameter validation for strategy: {strategy.config.strategy_id}")
            
            # Get strategy parameters
            parameters = self._extract_strategy_parameters(strategy)
            
            # Run parameter sensitivity analysis
            self._run_sensitivity_analysis(strategy, market_data, parameters)
            
            # Calculate parameter importance
            parameter_importance = self._calculate_parameter_importance()
            
            # Calculate parameter correlations
            parameter_correlations = self._calculate_parameter_correlations()
            
            # Calculate validation metrics
            parameter_stability = self._calculate_parameter_stability()
            optimal_parameters = self._find_optimal_parameters()
            parameter_robustness = self._calculate_parameter_robustness()
            
            # Create validation result
            result = ParameterValidationResult(
                strategy_id=strategy.config.strategy_id,
                strategy_name=strategy.config.name,
                parameter_sensitivities=self.sensitivities,
                parameter_importance=parameter_importance,
                parameter_correlations=parameter_correlations,
                parameter_stability=parameter_stability,
                optimal_parameters=optimal_parameters,
                parameter_robustness=parameter_robustness,
                validation_date=datetime.now()
            )
            
            # Create a summary validation result
            summary_result = self._create_summary_result(strategy, result)
            
            self.logger.info(f"Parameter validation completed. Parameters analyzed: {len(parameters)}")
            return summary_result
            
        except Exception as e:
            self.logger.error(f"Error in parameter validation: {e}")
            raise StrategyError(f"Parameter validation failed: {e}")
    
    def _extract_strategy_parameters(self, strategy: StrategyDefinition) -> Dict[str, float]:
        """Extract parameters from strategy configuration"""
        parameters = {}
        
        # Extract parameters from signal generation
        if hasattr(strategy.config, 'signal_generation') and strategy.config.signal_generation:
            for indicator in strategy.config.signal_generation.get('indicators', []):
                if 'parameters' in indicator:
                    for param_name, param_value in indicator['parameters'].items():
                        if isinstance(param_value, (int, float)):
                            parameters[f"{indicator['name']}_{param_name}"] = param_value
        
        # Extract parameters from risk management
        if hasattr(strategy.config, 'risk_management') and strategy.config.risk_management:
            risk_params = strategy.config.risk_management
            if 'position_sizing' in risk_params:
                for param_name, param_value in risk_params['position_sizing'].items():
                    if isinstance(param_value, (int, float)):
                        parameters[f"position_sizing_{param_name}"] = param_value
            
            if 'stop_loss' in risk_params:
                for param_name, param_value in risk_params['stop_loss'].items():
                    if isinstance(param_value, (int, float)):
                        parameters[f"stop_loss_{param_name}"] = param_value
            
            if 'take_profit' in risk_params:
                for param_name, param_value in risk_params['take_profit'].items():
                    if isinstance(param_value, (int, float)):
                        parameters[f"take_profit_{param_name}"] = param_value
        
        # Extract parameters from entry/exit logic
        if hasattr(strategy.config, 'entry_exit_logic') and strategy.config.entry_exit_logic:
            for param_name, param_value in strategy.config.entry_exit_logic.items():
                if isinstance(param_value, (int, float)):
                    parameters[f"entry_exit_{param_name}"] = param_value
        
        return parameters
    
    def _run_sensitivity_analysis(self, strategy: StrategyDefinition, market_data: Dict[str, pd.DataFrame], parameters: Dict[str, float]):
        """Run parameter sensitivity analysis"""
        self.sensitivities = []
        
        for param_name, base_value in parameters.items():
            try:
                self.logger.info(f"Analyzing parameter: {param_name}")
                
                # Generate test values
                test_values = self._generate_test_values(base_value)
                test_results = []
                
                # Test each value
                for test_value in test_values:
                    # Create modified strategy
                    modified_strategy = self._modify_strategy_parameter(strategy, param_name, test_value)
                    
                    # Run validation
                    validator = BacktestingValidator(self.config)
                    result = validator.validate_strategy(modified_strategy, market_data)
                    
                    # Store result (use Sharpe ratio as metric)
                    test_results.append(result.sharpe_ratio)
                
                # Calculate sensitivity metrics
                sensitivity_score = self._calculate_sensitivity_score(test_values, test_results)
                optimal_idx = np.argmax(test_results)
                optimal_value = test_values[optimal_idx]
                optimal_result = test_results[optimal_idx]
                
                # Create sensitivity result
                sensitivity = ParameterSensitivity(
                    parameter_name=param_name,
                    base_value=base_value,
                    test_values=test_values,
                    test_results=test_results,
                    sensitivity_score=sensitivity_score,
                    optimal_value=optimal_value,
                    optimal_result=optimal_result
                )
                
                self.sensitivities.append(sensitivity)
                self.parameter_results[param_name] = test_results
                
            except Exception as e:
                self.logger.warning(f"Error analyzing parameter {param_name}: {e}")
                continue
    
    def _generate_test_values(self, base_value: float) -> List[float]:
        """Generate test values for parameter sensitivity analysis"""
        if base_value == 0:
            # Handle zero values
            return [-0.1, -0.05, 0, 0.05, 0.1]
        
        # Check if this is an integer parameter (like RSI period)
        if isinstance(base_value, int) or base_value.is_integer():
            # For integer parameters, use integer values
            base_int = int(base_value)
            test_values = [
                max(1, base_int - 4),  # Ensure minimum value of 1
                max(1, base_int - 2),
                base_int,
                base_int + 2,
                base_int + 4
            ]
            return test_values
        
        # Generate values around base value for float parameters
        variations = [-0.5, -0.25, 0, 0.25, 0.5]  # -50%, -25%, 0%, +25%, +50%
        test_values = []
        
        for variation in variations:
            test_value = base_value * (1 + variation)
            test_values.append(test_value)
        
        return test_values
    
    def _modify_strategy_parameter(self, strategy: StrategyDefinition, param_name: str, new_value: float) -> StrategyDefinition:
        """Create a modified strategy with new parameter value"""
        # Create a copy of the strategy configuration
        import copy
        modified_config = copy.deepcopy(strategy.config)
        
        # Parse parameter name to find location
        if param_name.startswith('RSI_'):
            param_key = param_name[4:]  # Remove 'RSI_' prefix
            for indicator in modified_config.signal_generation.get('indicators', []):
                if indicator['name'] == 'RSI' and 'parameters' in indicator:
                    # Ensure integer parameters are properly handled
                    if param_key == 'period':
                        indicator['parameters'][param_key] = int(new_value)
                    else:
                        indicator['parameters'][param_key] = new_value
                    break
        
        elif param_name.startswith('MACD_'):
            param_key = param_name[6:]  # Remove 'MACD_' prefix
            for indicator in modified_config.signal_generation.get('indicators', []):
                if indicator['name'] == 'MACD' and 'parameters' in indicator:
                    # Ensure integer parameters are properly handled
                    if param_key in ['fast', 'slow', 'signal']:
                        indicator['parameters'][param_key] = int(new_value)
                    else:
                        indicator['parameters'][param_key] = new_value
                    break
        
        elif param_name.startswith('position_sizing_'):
            param_key = param_name[16:]  # Remove 'position_sizing_' prefix
            if 'position_sizing' in modified_config.risk_management:
                modified_config.risk_management['position_sizing'][param_key] = new_value
        
        elif param_name.startswith('stop_loss_'):
            param_key = param_name[11:]  # Remove 'stop_loss_' prefix
            if 'stop_loss' in modified_config.risk_management:
                modified_config.risk_management['stop_loss'][param_key] = new_value
        
        elif param_name.startswith('take_profit_'):
            param_key = param_name[13:]  # Remove 'take_profit_' prefix
            if 'take_profit' in modified_config.risk_management:
                modified_config.risk_management['take_profit'][param_key] = new_value
        
        elif param_name.startswith('entry_exit_'):
            param_key = param_name[11:]  # Remove 'entry_exit_' prefix
            if 'entry_exit_logic' in modified_config:
                modified_config.entry_exit_logic[param_key] = new_value
        
        # Create new strategy instance
        from strategy_layer.strategies import MomentumStrategyDefinition, PairTradingStrategyDefinition, MeanReversionStrategyDefinition
        
        if modified_config.strategy_type.value == 'momentum':
            return MomentumStrategyDefinition(modified_config)
        elif modified_config.strategy_type.value == 'pair_trading':
            return PairTradingStrategyDefinition(modified_config)
        elif modified_config.strategy_type.value == 'mean_reversion':
            return MeanReversionStrategyDefinition(modified_config)
        else:
            return strategy  # Return original if type not recognized
    
    def _calculate_sensitivity_score(self, test_values: List[float], test_results: List[float]) -> float:
        """Calculate sensitivity score for a parameter"""
        if len(test_values) < 2 or len(test_results) < 2:
            return 0.0
        
        # Calculate coefficient of variation of results
        results_std = np.std(test_results)
        results_mean = np.mean(test_results)
        
        if results_mean == 0:
            return 0.0
        
        cv = results_std / abs(results_mean)
        
        # Calculate range of results
        results_range = max(test_results) - min(test_results)
        
        # Combine metrics
        sensitivity_score = cv * results_range
        return sensitivity_score
    
    def _calculate_parameter_importance(self) -> Dict[str, float]:
        """Calculate parameter importance based on sensitivity scores"""
        importance = {}
        
        for sensitivity in self.sensitivities:
            importance[sensitivity.parameter_name] = sensitivity.sensitivity_score
        
        # Normalize importance scores
        if importance:
            max_importance = max(importance.values())
            if max_importance > 0:
                for param_name in importance:
                    importance[param_name] /= max_importance
        
        return importance
    
    def _calculate_parameter_correlations(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlations between parameters"""
        correlations = {}
        param_names = list(self.parameter_results.keys())
        
        for i, param1 in enumerate(param_names):
            correlations[param1] = {}
            for j, param2 in enumerate(param_names):
                if i == j:
                    correlations[param1][param2] = 1.0
                else:
                    # Calculate correlation between parameter results
                    results1 = self.parameter_results[param1]
                    results2 = self.parameter_results[param2]
                    
                    if len(results1) == len(results2) and len(results1) > 1:
                        correlation = np.corrcoef(results1, results2)[0, 1]
                        correlations[param1][param2] = correlation if not np.isnan(correlation) else 0.0
                    else:
                        correlations[param1][param2] = 0.0
        
        return correlations
    
    def _calculate_parameter_stability(self) -> float:
        """Calculate parameter stability score"""
        if not self.sensitivities:
            return 0.0
        
        # Calculate average sensitivity score
        avg_sensitivity = np.mean([s.sensitivity_score for s in self.sensitivities])
        
        # Calculate stability (inverse of sensitivity)
        stability = 1.0 / (1.0 + avg_sensitivity)
        return stability
    
    def _find_optimal_parameters(self) -> Dict[str, float]:
        """Find optimal parameter values"""
        optimal_params = {}
        
        for sensitivity in self.sensitivities:
            optimal_params[sensitivity.parameter_name] = sensitivity.optimal_value
        
        return optimal_params
    
    def _calculate_parameter_robustness(self) -> float:
        """Calculate parameter robustness score"""
        if not self.sensitivities:
            return 0.0
        
        # Calculate how close optimal values are to base values
        robustness_scores = []
        
        for sensitivity in self.sensitivities:
            if sensitivity.base_value != 0:
                deviation = abs(sensitivity.optimal_value - sensitivity.base_value) / abs(sensitivity.base_value)
                robustness = 1.0 / (1.0 + deviation)
                robustness_scores.append(robustness)
            else:
                # Handle zero base values
                deviation = abs(sensitivity.optimal_value)
                robustness = 1.0 / (1.0 + deviation)
                robustness_scores.append(robustness)
        
        return np.mean(robustness_scores) if robustness_scores else 0.0
    
    def _create_summary_result(self, strategy: StrategyDefinition, param_result: ParameterValidationResult) -> ValidationResult:
        """Create a summary validation result"""
        # Use the base strategy for a final validation
        validator = BacktestingValidator(self.config)
        
        # Create sample market data for validation
        sample_market_data = self._create_sample_market_data()
        
        # Run validation
        base_result = validator.validate_strategy(strategy, sample_market_data)
        
        # Modify result to include parameter validation info
        base_result.strategy_name = f"{base_result.strategy_name} (Parameter Validated)"
        
        return base_result
    
    def _create_sample_market_data(self) -> Dict[str, pd.DataFrame]:
        """Create sample market data for validation"""
        # This is a placeholder - in practice, you would use real market data
        dates = pd.date_range(start=self.config.start_date, end=self.config.end_date, freq='D')
        
        market_data = {}
        for symbol in self.config.symbols:
            # Generate sample price data
            np.random.seed(42)  # For reproducibility
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, len(dates))
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = pd.DataFrame({
                'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, len(dates))
            }, index=dates)
            
            market_data[symbol] = data
        
        return market_data
    
    def get_parameter_summary(self) -> Dict[str, Any]:
        """Get summary of parameter validation"""
        if not self.sensitivities:
            return {}
        
        return {
            'total_parameters': len(self.sensitivities),
            'avg_sensitivity': np.mean([s.sensitivity_score for s in self.sensitivities]),
            'max_sensitivity': max([s.sensitivity_score for s in self.sensitivities]),
            'min_sensitivity': min([s.sensitivity_score for s in self.sensitivities]),
            'parameter_stability': self._calculate_parameter_stability(),
            'parameter_robustness': self._calculate_parameter_robustness(),
            'most_sensitive_parameter': max(self.sensitivities, key=lambda x: x.sensitivity_score).parameter_name,
            'least_sensitive_parameter': min(self.sensitivities, key=lambda x: x.sensitivity_score).parameter_name
        }
    
    def get_sensitivity_analysis(self) -> List[Dict[str, Any]]:
        """Get detailed sensitivity analysis results"""
        return [s.to_dict() for s in self.sensitivities]
