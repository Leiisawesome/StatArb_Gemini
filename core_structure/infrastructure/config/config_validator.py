from typing import Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ValidationError:
    field: str
    message: str
    value: Any

class ConfigValidator:
    """Configuration validation and schema checking"""
    
    def __init__(self):
        self.schemas = self._load_validation_schemas()
    
    def validate_strategy_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy configuration"""
        errors = []
        
        # Required fields
        required_fields = ['name', 'version', 'parameters', 'risk_limits', 'timeframes', 'symbols']
        for field in required_fields:
            if field not in config:
                errors.append(ValidationError(field, f"Required field missing: {field}", None))
        
        # Parameter validation
        if 'parameters' in config:
            param_errors = self._validate_parameters(config['parameters'])
            errors.extend(param_errors)
        
        # Risk limits validation
        if 'risk_limits' in config:
            risk_errors = self._validate_risk_limits(config['risk_limits'])
            errors.extend(risk_errors)
        
        return errors
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> List[ValidationError]:
        """Validate strategy parameters based on academic research"""
        errors = []
        
        # Multi-horizon momentum parameters (Moskowitz et al., 2012)
        if 'momentum_lookback_short' in parameters:
            value = parameters['momentum_lookback_short']
            if not (1 <= value <= 50):
                errors.append(ValidationError(
                    'momentum_lookback_short', 
                    f"Value {value} out of academic range [1, 50] days", 
                    value
                ))
        
        if 'momentum_lookback_medium' in parameters:
            value = parameters['momentum_lookback_medium']
            if not (20 <= value <= 100):
                errors.append(ValidationError(
                    'momentum_lookback_medium', 
                    f"Value {value} out of academic range [20, 100] days", 
                    value
                ))
        
        if 'momentum_lookback_long' in parameters:
            value = parameters['momentum_lookback_long']
            if not (50 <= value <= 150):
                errors.append(ValidationError(
                    'momentum_lookback_long', 
                    f"Value {value} out of academic range [50, 150] days", 
                    value
                ))
        
        # Volume parameters (Gervais et al., 2001)
        if 'volume_weight' in parameters:
            value = parameters['volume_weight']
            if not (0.0 <= value <= 1.0):
                errors.append(ValidationError(
                    'volume_weight', 
                    f"Value {value} out of range [0.0, 1.0]", 
                    value
                ))
        
        if 'volume_threshold' in parameters:
            value = parameters['volume_threshold']
            if not (100000 <= value <= 10000000):  # $100K to $10M
                errors.append(ValidationError(
                    'volume_threshold', 
                    f"Value {value} out of reasonable range [$100K, $10M]", 
                    value
                ))
        
        # Regime detection parameters (Cooper et al., 2004)
        if 'regime_lookback' in parameters:
            value = parameters['regime_lookback']
            if not (100 <= value <= 500):
                errors.append(ValidationError(
                    'regime_lookback', 
                    f"Value {value} out of range [100, 500] days", 
                    value
                ))
        
        if 'volatility_threshold' in parameters:
            value = parameters['volatility_threshold']
            if not (0.1 <= value <= 0.5):
                errors.append(ValidationError(
                    'volatility_threshold', 
                    f"Value {value} out of range [0.1, 0.5] (10-50%)", 
                    value
                ))
        
        # Crash protection parameters (Daniel & Moskowitz, 2016)
        if 'crash_volatility_threshold' in parameters:
            value = parameters['crash_volatility_threshold']
            if not (0.2 <= value <= 0.6):
                errors.append(ValidationError(
                    'crash_volatility_threshold', 
                    f"Value {value} out of range [0.2, 0.6] (20-60%)", 
                    value
                ))
        
        if 'crash_market_drawdown_threshold' in parameters:
            value = parameters['crash_market_drawdown_threshold']
            if not (-0.3 <= value <= -0.05):
                errors.append(ValidationError(
                    'crash_market_drawdown_threshold', 
                    f"Value {value} out of range [-0.3, -0.05] (-30% to -5%)", 
                    value
                ))
        
        # Position sizing parameters
        if 'position_size' in parameters:
            value = parameters['position_size']
            if not (0.01 <= value <= 1.0):
                errors.append(ValidationError(
                    'position_size', 
                    f"Value {value} out of range [0.01, 1.0]", 
                    value
                ))
        
        if 'max_positions' in parameters:
            value = parameters['max_positions']
            if not (1 <= value <= 50):
                errors.append(ValidationError(
                    'max_positions', 
                    f"Value {value} out of range [1, 50]", 
                    value
                ))
        
        # Signal thresholds
        if 'signal_threshold' in parameters:
            value = parameters['signal_threshold']
            if not (0.1 <= value <= 2.0):
                errors.append(ValidationError(
                    'signal_threshold', 
                    f"Value {value} out of range [0.1, 2.0]", 
                    value
                ))
        
        return errors
    
    def _validate_risk_limits(self, risk_limits: Dict[str, Any]) -> List[ValidationError]:
        """Validate risk limits"""
        errors = []
        
        if 'max_daily_loss' in risk_limits:
            value = risk_limits['max_daily_loss']
            if not (0.001 <= value <= 0.1):
                errors.append(ValidationError(
                    'max_daily_loss', 
                    f"Value {value} out of range [0.001, 0.1] (0.1% to 10%)", 
                    value
                ))
        
        if 'max_drawdown' in risk_limits:
            value = risk_limits['max_drawdown']
            if not (0.05 <= value <= 0.5):
                errors.append(ValidationError(
                    'max_drawdown', 
                    f"Value {value} out of range [0.05, 0.5] (5% to 50%)", 
                    value
                ))
        
        if 'max_position_value' in risk_limits:
            value = risk_limits['max_position_value']
            if not (100000 <= value <= 10000000):  # $100K to $10M
                errors.append(ValidationError(
                    'max_position_value', 
                    f"Value {value} out of range [$100K, $10M]", 
                    value
                ))
        
        return errors
    
    def validate_enhanced_config(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate enhanced configuration"""
        errors = []
        
        # Environment validation
        if 'environment' not in config:
            errors.append(ValidationError('environment', 'Environment field required', None))
        elif config['environment'] not in ['development', 'backtesting', 'production', 'real_time']:
            errors.append(ValidationError('environment', f"Invalid environment: {config['environment']}", config['environment']))
        
        # Strategy validation
        if 'strategy' in config:
            strategy_errors = self.validate_strategy_config(config['strategy'])
            errors.extend(strategy_errors)
        
        # Training configuration validation
        if 'training' in config and config['training']:
            training_errors = self._validate_training_config(config['training'])
            errors.extend(training_errors)
        
        # Trading configuration validation
        if 'trading' in config:
            trading_errors = self._validate_trading_config(config['trading'])
            errors.extend(trading_errors)
        
        return errors
    
    def _validate_training_config(self, training: Dict[str, Any]) -> List[ValidationError]:
        """Validate training configuration"""
        errors = []
        
        # Date validation
        if 'start_date' not in training:
            errors.append(ValidationError('training.start_date', 'Training start date required', None))
        
        if 'end_date' not in training:
            errors.append(ValidationError('training.end_date', 'Training end date required', None))
        
        # Validation split
        if 'validation_split' in training:
            value = training['validation_split']
            if not (0.1 <= value <= 0.5):
                errors.append(ValidationError(
                    'training.validation_split', 
                    f"Value {value} out of range [0.1, 0.5]", 
                    value
                ))
        
        # Optimization method
        if 'optimization_method' in training:
            value = training['optimization_method']
            if value not in ['grid_search', 'bayesian', 'genetic']:
                errors.append(ValidationError(
                    'training.optimization_method', 
                    f"Invalid method: {value}. Must be one of: grid_search, bayesian, genetic", 
                    value
                ))
        
        return errors
    
    def _validate_trading_config(self, trading: Dict[str, Any]) -> List[ValidationError]:
        """Validate trading configuration"""
        errors = []
        
        # Date validation
        if 'start_date' not in trading:
            errors.append(ValidationError('trading.start_date', 'Trading start date required', None))
        
        # Execution mode
        if 'execution_mode' in trading:
            value = trading['execution_mode']
            if value not in ['simulation', 'paper', 'live']:
                errors.append(ValidationError(
                    'trading.execution_mode', 
                    f"Invalid mode: {value}. Must be one of: simulation, paper, live", 
                    value
                ))
        
        # Position sizing
        if 'position_sizing' in trading:
            value = trading['position_sizing']
            if value not in ['fixed', 'kelly', 'volatility_targeting']:
                errors.append(ValidationError(
                    'trading.position_sizing', 
                    f"Invalid sizing: {value}. Must be one of: fixed, kelly, volatility_targeting", 
                    value
                ))
        
        return errors
    
    def _load_validation_schemas(self) -> Dict[str, Any]:
        """Load JSON schemas for validation"""
        return {
            'strategy': {
                'type': 'object',
                'required': ['name', 'version', 'parameters', 'risk_limits'],
                'properties': {
                    'name': {'type': 'string'},
                    'version': {'type': 'string'},
                    'parameters': {'type': 'object'},
                    'risk_limits': {'type': 'object'},
                    'timeframes': {'type': 'array', 'items': {'type': 'string'}},
                    'symbols': {'type': 'array', 'items': {'type': 'string'}}
                }
            },
            'enhanced_config': {
                'type': 'object',
                'required': ['environment', 'strategy', 'trading'],
                'properties': {
                    'environment': {'type': 'string', 'enum': ['development', 'backtesting', 'production', 'real_time']},
                    'strategy': {'$ref': '#/definitions/strategy'},
                    'training': {'type': 'object'},
                    'trading': {'type': 'object'},
                    'database': {'type': 'object'},
                    'data_feeds': {'type': 'object'},
                    'execution': {'type': 'object'},
                    'risk_management': {'type': 'object'},
                    'logging': {'type': 'object'}
                },
                'definitions': {
                    'strategy': {'$ref': '#/definitions/strategy'}
                }
            }
        }
    
    def print_validation_errors(self, errors: List[ValidationError]):
        """Print validation errors in a readable format"""
        if not errors:
            logger.info("Configuration validation passed")
            return
        
        logger.error(f"Configuration validation failed with {len(errors)} errors:")
        for error in errors:
            logger.error(f"  {error.field}: {error.message} (value: {error.value})")
    
    def is_valid(self, errors: List[ValidationError]) -> bool:
        """Check if configuration is valid"""
        return len(errors) == 0 