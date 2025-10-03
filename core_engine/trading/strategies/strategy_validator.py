"""
Strategy Engine - Strategy Validator
Comprehensive strategy validation, testing, and quality assurance
"""

import logging
import numpy as np
import pandas as pd
import uuid
import asyncio
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
import inspect
from pathlib import Path
from collections import deque

# Import strategy components
from .strategy_engine import BaseStrategy

# Import ISystemComponent for orchestrator integration
try:
    from ...system.interfaces import ISystemComponent
except ImportError:
    # Fallback definition
    from abc import ABC, abstractmethod
    class ISystemComponent(ABC):
        @abstractmethod
        async def initialize(self) -> bool:
            pass
        
        @abstractmethod
        async def start(self) -> bool:
            pass
        
        @abstractmethod
        async def stop(self) -> bool:
            pass
        
        @abstractmethod
        async def health_check(self) -> Dict[str, Any]:
            pass
        
        @abstractmethod
        def get_status(self) -> Dict[str, Any]:
            pass

# Mock backtest types (temporary until proper backtest module is available)
@dataclass
class BacktestConfig:
    """Mock backtest configuration"""
    strategy_id: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 100000.0

@dataclass
class BacktestResult:
    """Mock backtest result"""
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels"""
    BASIC = "basic"           # Basic syntax and interface validation
    STANDARD = "standard"     # Standard validation with basic tests
    COMPREHENSIVE = "comprehensive"  # Full validation with extensive testing
    PRODUCTION = "production"  # Production-ready validation


class ValidationStatus(Enum):
    """Validation status"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class ValidationCategory(Enum):
    """Validation categories"""
    CODE_QUALITY = "code_quality"
    INTERFACE_COMPLIANCE = "interface_compliance"
    PARAMETER_VALIDATION = "parameter_validation"
    DATA_HANDLING = "data_handling"
    RISK_MANAGEMENT = "risk_management"
    PERFORMANCE = "performance"
    BACKTESTING = "backtesting"
    STATISTICAL = "statistical"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    
    category: ValidationCategory
    severity: str  # "error", "warning", "info"
    title: str
    description: str
    suggestion: str = ""
    line_number: Optional[int] = None
    code_snippet: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    validator_name: str = ""


@dataclass
class ValidationResult:
    """Result of strategy validation"""
    
    # Basic info
    strategy_id: str = ""
    validation_level: ValidationLevel = ValidationLevel.BASIC
    overall_status: ValidationStatus = ValidationStatus.FAILED
    
    # Issues tracking
    issues: List[ValidationIssue] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Scores (0-100)
    overall_score: float = 0.0
    category_scores: Dict[ValidationCategory, float] = field(default_factory=dict)
    
    # Performance metrics
    validation_time: float = 0.0
    memory_usage: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Detailed results
    code_analysis: Dict[str, Any] = field(default_factory=dict)
    parameter_analysis: Dict[str, Any] = field(default_factory=dict)
    backtest_results: Optional[BacktestResult] = None
    
    # Metadata
    validation_timestamp: datetime = field(default_factory=datetime.now)
    validator_version: str = "1.0.0"


class CodeAnalyzer:
    """Analyze strategy code quality and compliance"""
    
    def __init__(self):
        self.required_methods = [
            'initialize', 'update', 'generate_signals', 'get_metrics'
        ]
        self.recommended_methods = [
            'validate_parameters', 'cleanup', 'on_market_open', 'on_market_close'
        ]
        
        logger.info("Code analyzer initialized")
    
    def analyze_strategy_code(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """Analyze strategy code for quality and compliance"""
        
        try:
            analysis = {
                'class_analysis': {},
                'method_analysis': {},
                'parameter_analysis': {},
                'inheritance_analysis': {},
                'code_quality': {},
                'issues': []
            }
            
            strategy_class = strategy.__class__
            
            # Class analysis
            analysis['class_analysis'] = self._analyze_class_structure(strategy_class)
            
            # Method analysis
            analysis['method_analysis'] = self._analyze_methods(strategy_class)
            
            # Parameter analysis
            analysis['parameter_analysis'] = self._analyze_parameters(strategy)
            
            # Inheritance analysis
            analysis['inheritance_analysis'] = self._analyze_inheritance(strategy_class)
            
            # Code quality analysis
            analysis['code_quality'] = self._analyze_code_quality(strategy_class)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing strategy code: {e}")
            return {'error': str(e)}
    
    def _analyze_class_structure(self, strategy_class: type) -> Dict[str, Any]:
        """Analyze class structure"""
        
        try:
            structure = {
                'class_name': strategy_class.__name__,
                'module': strategy_class.__module__,
                'docstring': strategy_class.__doc__,
                'has_docstring': bool(strategy_class.__doc__),
                'attributes': [],
                'class_variables': [],
                'methods': []
            }
            
            # Get class attributes
            for name, value in inspect.getmembers(strategy_class):
                if not name.startswith('_'):
                    if inspect.ismethod(value) or inspect.isfunction(value):
                        structure['methods'].append(name)
                    else:
                        structure['attributes'].append(name)
            
            # Get class variables
            for name in dir(strategy_class):
                if not name.startswith('_') and hasattr(strategy_class, name):
                    attr = getattr(strategy_class, name)
                    if not callable(attr):
                        structure['class_variables'].append(name)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing class structure: {e}")
            return {}
    
    def _analyze_methods(self, strategy_class: type) -> Dict[str, Any]:
        """Analyze method implementation"""
        
        try:
            method_analysis = {
                'required_methods': {},
                'recommended_methods': {},
                'custom_methods': [],
                'method_signatures': {},
                'method_complexity': {}
            }
            
            # Check required methods
            for method_name in self.required_methods:
                if hasattr(strategy_class, method_name):
                    method = getattr(strategy_class, method_name)
                    method_analysis['required_methods'][method_name] = {
                        'exists': True,
                        'signature': str(inspect.signature(method)),
                        'docstring': method.__doc__,
                        'has_docstring': bool(method.__doc__)
                    }
                else:
                    method_analysis['required_methods'][method_name] = {'exists': False}
            
            # Check recommended methods
            for method_name in self.recommended_methods:
                if hasattr(strategy_class, method_name):
                    method = getattr(strategy_class, method_name)
                    method_analysis['recommended_methods'][method_name] = {
                        'exists': True,
                        'signature': str(inspect.signature(method)),
                        'docstring': method.__doc__
                    }
                else:
                    method_analysis['recommended_methods'][method_name] = {'exists': False}
            
            # Find custom methods
            all_methods = [name for name, _ in inspect.getmembers(strategy_class, inspect.ismethod)]
            all_methods.extend([name for name, _ in inspect.getmembers(strategy_class, inspect.isfunction)])
            
            standard_methods = self.required_methods + self.recommended_methods + ['__init__']
            custom_methods = [m for m in all_methods if not m.startswith('_') and m not in standard_methods]
            method_analysis['custom_methods'] = custom_methods
            
            # Analyze method signatures and complexity
            for method_name in all_methods:
                if hasattr(strategy_class, method_name):
                    method = getattr(strategy_class, method_name)
                    try:
                        signature = inspect.signature(method)
                        method_analysis['method_signatures'][method_name] = str(signature)
                        
                        # Simple complexity analysis
                        source_lines = inspect.getsourcelines(method)[0] if inspect.ismethod(method) or inspect.isfunction(method) else []
                        complexity = len(source_lines)
                        method_analysis['method_complexity'][method_name] = complexity
                        
                    except Exception as e:
                        logger.warning(f"Could not analyze method {method_name}: {e}")
            
            return method_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing methods: {e}")
            return {}
    
    def _analyze_parameters(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """Analyze strategy parameters"""
        
        try:
            param_analysis = {
                'config_exists': hasattr(strategy, 'config'),
                'parameter_count': 0,
                'parameter_types': {},
                'default_values': {},
                'validation_methods': []
            }
            
            if hasattr(strategy, 'config') and strategy.config:
                config = strategy.config
                
                # Count parameters
                if hasattr(config, '__dict__'):
                    params = {k: v for k, v in config.__dict__.items() if not k.startswith('_')}
                    param_analysis['parameter_count'] = len(params)
                    
                    # Analyze parameter types and defaults
                    for name, value in params.items():
                        param_analysis['parameter_types'][name] = type(value).__name__
                        param_analysis['default_values'][name] = value
                
                # Check for validation methods
                if hasattr(strategy, 'validate_parameters'):
                    param_analysis['validation_methods'].append('validate_parameters')
                if hasattr(config, 'validate'):
                    param_analysis['validation_methods'].append('config.validate')
            
            return param_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing parameters: {e}")
            return {}
    
    def _analyze_inheritance(self, strategy_class: type) -> Dict[str, Any]:
        """Analyze class inheritance"""
        
        try:
            inheritance = {
                'base_classes': [base.__name__ for base in strategy_class.__bases__],
                'mro': [cls.__name__ for cls in strategy_class.__mro__],
                'inherits_from_base_strategy': False,
                'abstract_methods': []
            }
            
            # Check if inherits from BaseStrategy
            for base in strategy_class.__mro__:
                if base.__name__ == 'BaseStrategy':
                    inheritance['inherits_from_base_strategy'] = True
                    break
            
            # Check for abstract methods
            if hasattr(strategy_class, '__abstractmethods__'):
                inheritance['abstract_methods'] = list(strategy_class.__abstractmethods__)
            
            return inheritance
            
        except Exception as e:
            logger.error(f"Error analyzing inheritance: {e}")
            return {}
    
    def _analyze_code_quality(self, strategy_class: type) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        
        try:
            quality = {
                'has_type_hints': False,
                'docstring_coverage': 0.0,
                'method_count': 0,
                'average_method_length': 0.0,
                'complexity_score': 0.0
            }
            
            methods = inspect.getmembers(strategy_class, inspect.ismethod)
            methods.extend(inspect.getmembers(strategy_class, inspect.isfunction))
            
            quality['method_count'] = len(methods)
            
            if methods:
                # Calculate docstring coverage
                documented_methods = sum(1 for _, method in methods if method.__doc__)
                quality['docstring_coverage'] = documented_methods / len(methods)
                
                # Calculate average method length
                total_lines = 0
                for _, method in methods:
                    try:
                        source_lines = inspect.getsourcelines(method)[0]
                        total_lines += len(source_lines)
                    except:
                        pass
                
                quality['average_method_length'] = total_lines / len(methods) if methods else 0
                
                # Simple complexity score (lower is better)
                quality['complexity_score'] = min(100, quality['average_method_length'] * 2)
            
            # Check for type hints (simplified check)
            try:
                source = inspect.getsource(strategy_class)
                has_annotations = '->' in source or ': ' in source
                quality['has_type_hints'] = has_annotations
            except:
                pass
            
            return quality
            
        except Exception as e:
            logger.error(f"Error analyzing code quality: {e}")
            return {}


class ParameterValidator:
    """Validate strategy parameters"""
    
    def __init__(self):
        self.numeric_params = ['lookback_period', 'threshold', 'stop_loss', 'take_profit']
        self.boolean_params = ['allow_shorts', 'use_stops', 'enable_logging']
        self.string_params = ['symbol', 'mode', 'name']
        
        logger.info("Parameter validator initialized")
    
    def validate_parameters(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """Validate strategy parameters"""
        
        try:
            validation = {
                'config_exists': False,
                'parameter_checks': {},
                'range_checks': {},
                'type_checks': {},
                'consistency_checks': {},
                'issues': []
            }
            
            if not hasattr(strategy, 'config') or not strategy.config:
                validation['issues'].append("Strategy config missing")
                return validation
            
            validation['config_exists'] = True
            config = strategy.config
            
            # Get all parameters
            if hasattr(config, '__dict__'):
                params = {k: v for k, v in config.__dict__.items() if not k.startswith('_')}
                
                # Type checks
                validation['type_checks'] = self._check_parameter_types(params)
                
                # Range checks
                validation['range_checks'] = self._check_parameter_ranges(params)
                
                # Consistency checks
                validation['consistency_checks'] = self._check_parameter_consistency(params)
                
                # Collect issues
                for check_type, checks in validation.items():
                    if isinstance(checks, dict):
                        for param, result in checks.items():
                            if isinstance(result, dict) and not result.get('valid', True):
                                validation['issues'].append(f"{check_type}: {param} - {result.get('message', 'Invalid')}")
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            return {'error': str(e)}
    
    def _check_parameter_types(self, params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Check parameter types"""
        
        type_checks = {}
        
        for name, value in params.items():
            check_result = {'valid': True, 'expected_type': None, 'actual_type': type(value).__name__}
            
            # Check numeric parameters
            if any(keyword in name.lower() for keyword in self.numeric_params):
                if not isinstance(value, (int, float)):
                    check_result['valid'] = False
                    check_result['expected_type'] = 'numeric'
                    check_result['message'] = f"Expected numeric type, got {type(value).__name__}"
            
            # Check boolean parameters
            elif any(keyword in name.lower() for keyword in self.boolean_params):
                if not isinstance(value, bool):
                    check_result['valid'] = False
                    check_result['expected_type'] = 'bool'
                    check_result['message'] = f"Expected boolean type, got {type(value).__name__}"
            
            # Check string parameters
            elif any(keyword in name.lower() for keyword in self.string_params):
                if not isinstance(value, str):
                    check_result['valid'] = False
                    check_result['expected_type'] = 'str'
                    check_result['message'] = f"Expected string type, got {type(value).__name__}"
            
            type_checks[name] = check_result
        
        return type_checks
    
    def _check_parameter_ranges(self, params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Check parameter value ranges"""
        
        range_checks = {}
        
        for name, value in params.items():
            check_result = {'valid': True, 'range': None}
            
            # Check common parameter ranges
            if 'period' in name.lower() and isinstance(value, (int, float)):
                if value <= 0:
                    check_result['valid'] = False
                    check_result['message'] = "Period must be positive"
                    check_result['range'] = '> 0'
            
            elif 'threshold' in name.lower() and isinstance(value, (int, float)):
                if value < 0:
                    check_result['valid'] = False
                    check_result['message'] = "Threshold should be non-negative"
                    check_result['range'] = '>= 0'
            
            elif 'stop_loss' in name.lower() and isinstance(value, (int, float)):
                if not 0 <= value <= 1:
                    check_result['valid'] = False
                    check_result['message'] = "Stop loss should be between 0 and 1"
                    check_result['range'] = '0 <= x <= 1'
            
            elif 'take_profit' in name.lower() and isinstance(value, (int, float)):
                if value <= 0:
                    check_result['valid'] = False
                    check_result['message'] = "Take profit should be positive"
                    check_result['range'] = '> 0'
            
            range_checks[name] = check_result
        
        return range_checks
    
    def _check_parameter_consistency(self, params: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Check parameter consistency"""
        
        consistency_checks = {}
        
        # Check stop loss vs take profit
        stop_loss = None
        take_profit = None
        
        for name, value in params.items():
            if 'stop_loss' in name.lower() and isinstance(value, (int, float)):
                stop_loss = value
            elif 'take_profit' in name.lower() and isinstance(value, (int, float)):
                take_profit = value
        
        if stop_loss is not None and take_profit is not None:
            consistency_checks['stop_loss_take_profit'] = {
                'valid': True,
                'message': "Stop loss and take profit are consistent"
            }
            
            # Basic consistency check - stop loss should be smaller than take profit for risk management
            if stop_loss > take_profit:
                consistency_checks['stop_loss_take_profit']['valid'] = False
                consistency_checks['stop_loss_take_profit']['message'] = "Stop loss is larger than take profit"
        
        return consistency_checks


class DataValidator:
    """Validate strategy data handling"""
    
    def __init__(self):
        logger.info("Data validator initialized")
    
    def validate_data_handling(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Validate strategy data handling capabilities"""
        
        try:
            validation = {
                'data_compatibility': {},
                'missing_data_handling': {},
                'data_quality_checks': {},
                'performance_checks': {},
                'issues': []
            }
            
            # Test data compatibility
            validation['data_compatibility'] = self._test_data_compatibility(strategy, sample_data)
            
            # Test missing data handling
            validation['missing_data_handling'] = self._test_missing_data_handling(strategy, sample_data)
            
            # Test data quality handling
            validation['data_quality_checks'] = self._test_data_quality_handling(strategy, sample_data)
            
            # Test performance with large datasets
            validation['performance_checks'] = self._test_data_performance(strategy, sample_data)
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating data handling: {e}")
            return {'error': str(e)}
    
    def _test_data_compatibility(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test strategy compatibility with different data formats"""
        
        try:
            compatibility = {
                'accepts_dict_input': False,
                'handles_multiple_symbols': False,
                'processes_standard_columns': False,
                'error_handling': False
            }
            
            # Test basic data input
            try:
                strategy.update(sample_data)
                compatibility['accepts_dict_input'] = True
                compatibility['handles_multiple_symbols'] = len(sample_data) > 1
            except Exception as e:
                compatibility['error'] = str(e)
            
            # Test standard column handling
            if sample_data:
                sample_symbol = list(sample_data.keys())[0]
                sample_df = sample_data[sample_symbol]
                
                standard_columns = ['open', 'high', 'low', 'close', 'volume']
                has_standard_columns = any(col in sample_df.columns for col in standard_columns)
                compatibility['processes_standard_columns'] = has_standard_columns
            
            return compatibility
            
        except Exception as e:
            logger.error(f"Error testing data compatibility: {e}")
            return {'error': str(e)}
    
    def _test_missing_data_handling(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test strategy handling of missing data"""
        
        try:
            missing_data_test = {
                'handles_missing_values': False,
                'handles_missing_symbols': False,
                'handles_incomplete_data': False
            }
            
            if not sample_data:
                return missing_data_test
            
            # Create test data with missing values
            test_data = {}
            for symbol, data in sample_data.items():
                test_df = data.copy()
                
                # Introduce missing values
                if len(test_df) > 10:
                    missing_indices = np.random.choice(test_df.index, size=min(5, len(test_df)//4), replace=False)
                    test_df.loc[missing_indices, test_df.columns[0]] = np.nan
                
                test_data[symbol] = test_df
            
            # Test strategy with missing data
            try:
                strategy.update(test_data)
                missing_data_test['handles_missing_values'] = True
            except Exception as e:
                missing_data_test['missing_values_error'] = str(e)
            
            # Test with empty symbol data
            try:
                empty_data = {symbol: pd.DataFrame() for symbol in list(sample_data.keys())[:1]}
                strategy.update(empty_data)
                missing_data_test['handles_incomplete_data'] = True
            except Exception as e:
                missing_data_test['incomplete_data_error'] = str(e)
            
            return missing_data_test
            
        except Exception as e:
            logger.error(f"Error testing missing data handling: {e}")
            return {'error': str(e)}
    
    def _test_data_quality_handling(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test strategy handling of data quality issues"""
        
        try:
            quality_test = {
                'handles_outliers': False,
                'handles_duplicates': False,
                'handles_inconsistent_dates': False
            }
            
            if not sample_data:
                return quality_test
            
            # Test with outliers
            for symbol, data in sample_data.items():
                if len(data) > 5:
                    test_data = data.copy()
                    
                    # Introduce outliers
                    outlier_col = test_data.select_dtypes(include=[np.number]).columns[0]
                    test_data.iloc[0, test_data.columns.get_loc(outlier_col)] *= 1000
                    
                    try:
                        strategy.update({symbol: test_data})
                        quality_test['handles_outliers'] = True
                    except Exception as e:
                        quality_test['outliers_error'] = str(e)
                    
                    break
            
            return quality_test
            
        except Exception as e:
            logger.error(f"Error testing data quality handling: {e}")
            return {'error': str(e)}
    
    def _test_data_performance(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test strategy performance with data"""
        
        try:
            performance_test = {
                'processing_time': 0.0,
                'memory_efficient': True,
                'scales_with_data': True
            }
            
            if not sample_data:
                return performance_test
            
            # Test processing time
            start_time = time.time()
            try:
                strategy.update(sample_data)
                processing_time = time.time() - start_time
                performance_test['processing_time'] = processing_time
                
                # Reasonable processing time threshold (can be adjusted)
                performance_test['acceptable_speed'] = processing_time < 1.0
                
            except Exception as e:
                performance_test['performance_error'] = str(e)
            
            return performance_test
            
        except Exception as e:
            logger.error(f"Error testing data performance: {e}")
            return {'error': str(e)}


class EnhancedStrategyValidator(ISystemComponent):
    """
    Enhanced Comprehensive Strategy Validator with ISystemComponent Integration
    
    Provides multi-level validation for trading strategies including code quality,
    parameter validation, data handling, risk management, performance testing,
    and orchestrator integration for institutional-grade validation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize enhanced strategy validator"""
        
        # Configuration
        self.config = config or {}
        self.validation_level = ValidationLevel(self.config.get('validation_level', 'standard'))
        
        # ISystemComponent state management
        self.component_id = str(uuid.uuid4())
        self.is_initialized = False
        self.is_operational = False
        self.last_error: Optional[str] = None
        self.initialization_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        # Orchestrator integration
        self.orchestrator: Optional[Any] = None  # HierarchicalSystemOrchestrator reference
        
        # Initialize sub-validators
        self.code_analyzer = CodeAnalyzer()
        self.parameter_validator = ParameterValidator()
        self.data_validator = DataValidator()
        
        # Validation weights (for scoring)
        self.validation_weights = {
            ValidationCategory.CODE_QUALITY: 0.15,
            ValidationCategory.INTERFACE_COMPLIANCE: 0.20,
            ValidationCategory.PARAMETER_VALIDATION: 0.15,
            ValidationCategory.DATA_HANDLING: 0.15,
            ValidationCategory.RISK_MANAGEMENT: 0.10,
            ValidationCategory.PERFORMANCE: 0.10,
            ValidationCategory.BACKTESTING: 0.10,
            ValidationCategory.STATISTICAL: 0.05
        }
        
        # Enhanced configuration
        self.enable_caching = self.config.get('enable_caching', True)
        self.enable_performance_monitoring = self.config.get('enable_performance_monitoring', True)
        self.enable_detailed_reporting = self.config.get('enable_detailed_reporting', True)
        self.validation_timeout = self.config.get('validation_timeout', 300)  # 5 minutes
        self.parallel_validation = self.config.get('parallel_validation', True)
        
        # Component health tracking
        self.health_metrics = {
            'component_type': 'EnhancedStrategyValidator',
            'initialization_status': 'pending',
            'operational_status': 'inactive',
            'last_health_check': None,
            'error_count': 0,
            'warning_count': 0,
            'performance_metrics': {
                'total_validations': 0,
                'successful_validations': 0,
                'failed_validations': 0,
                'avg_validation_time': 0.0,
                'validation_cache_hits': 0,
                'validation_cache_misses': 0
            }
        }
        
        # Enhanced features
        self._validation_cache = {} if self.enable_caching else None
        self._validation_history = deque(maxlen=1000)  # Keep last 1000 validations
        self._performance_benchmarks = {}
        
        logger.info(f"🚀 Enhanced Strategy Validator initialized with {self.validation_level.value} level and component ID: {self.component_id}")
    
    # ========================================
    # ORCHESTRATOR INTEGRATION
    # ========================================
    
    def register_with_orchestrator(self, orchestrator) -> str:
        """Register component with HierarchicalSystemOrchestrator"""
        from core_engine.system.hierarchical_orchestrator import ComponentLayer, AuthorityLevel
        
        self.orchestrator = orchestrator
        self.component_id = orchestrator.register_component(
            name="EnhancedStrategyValidator",
            component=self,
            layer=ComponentLayer.EXECUTION,
            authority_level=AuthorityLevel.OPERATIONAL,
            initialization_order=26  # Before strategy execution
        )
        
        logger.info(f"✅ EnhancedStrategyValidator registered with orchestrator: {self.component_id}")
        return self.component_id
    
    async def request_operation_authorization(self, operation: str, details: Dict[str, Any]) -> bool:
        """Request authorization from orchestrator for privileged operations"""
        if not self.orchestrator or not self.component_id:
            logger.warning("No orchestrator available for authorization request")
            return False
        
        return await self.orchestrator.request_system_authorization(
            operation, self.component_id, details
        )
    
    # ========================================
    # ISystemComponent Implementation
    # ========================================
    async def initialize(self) -> bool:
        """Initialize the enhanced strategy validator"""
        try:
            logger.info("🔄 Initializing Enhanced Strategy Validator...")
            
            self.initialization_time = datetime.now()
            
            # Initialize sub-validators
            self.code_analyzer = CodeAnalyzer()
            self.parameter_validator = ParameterValidator()
            self.data_validator = DataValidator()
            
            # Initialize enhanced features
            await self._initialize_caching_system()
            await self._initialize_performance_monitoring()
            await self._initialize_benchmarking_system()
            
            # Load validation benchmarks
            await self._load_validation_benchmarks()
            
            self.is_initialized = True
            self.health_metrics['initialization_status'] = 'completed'
            
            logger.info("✅ Enhanced Strategy Validator initialization complete")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.health_metrics['initialization_status'] = 'failed'
            self.health_metrics['error_count'] += 1
            logger.error(f"❌ Enhanced Strategy Validator initialization failed: {e}")
            return False
    
    async def start(self) -> bool:
        """Start the enhanced strategy validator"""
        try:
            if not self.is_initialized:
                logger.error("❌ Cannot start - Enhanced Strategy Validator not initialized")
                return False
            
            logger.info("🚀 Starting Enhanced Strategy Validator...")
            
            self.start_time = datetime.now()
            
            # Start monitoring systems
            if self.enable_performance_monitoring:
                await self._start_performance_monitoring()
            
            self.is_operational = True
            self.health_metrics['operational_status'] = 'active'
            
            logger.info("✅ Enhanced Strategy Validator started successfully")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.health_metrics['error_count'] += 1
            logger.error(f"❌ Failed to start Enhanced Strategy Validator: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the enhanced strategy validator"""
        try:
            logger.info("🛑 Stopping Enhanced Strategy Validator...")
            
            # Stop monitoring tasks
            if hasattr(self, '_monitoring_task') and self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Save validation history and benchmarks
            await self._save_validation_data()
            
            self.is_operational = False
            self.health_metrics['operational_status'] = 'stopped'
            
            logger.info("✅ Enhanced Strategy Validator stopped successfully")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.health_metrics['error_count'] += 1
            logger.error(f"❌ Failed to stop Enhanced Strategy Validator: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        try:
            health_status = {
                'healthy': True,
                'component_id': self.component_id,
                'component_type': 'EnhancedStrategyValidator',
                'initialized': self.is_initialized,
                'operational': self.is_operational,
                'validation_level': self.validation_level.value,
                'last_error': self.last_error,
                'uptime_seconds': 0,
                'performance_metrics': self.health_metrics['performance_metrics'].copy(),
                'error_count': self.health_metrics['error_count'],
                'warning_count': self.health_metrics['warning_count']
            }
            
            # Calculate uptime
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds()
                health_status['uptime_seconds'] = uptime
            
            # Check cache health
            if self.enable_caching and self._validation_cache:
                cache_size = len(self._validation_cache)
                health_status['cache_size'] = cache_size
                if cache_size > 10000:  # Large cache warning
                    health_status['healthy'] = False
                    health_status['warning'] = "Validation cache size is very large"
            
            # Check validation success rate
            total_validations = self.health_metrics['performance_metrics']['total_validations']
            successful_validations = self.health_metrics['performance_metrics']['successful_validations']
            
            if total_validations > 0:
                success_rate = successful_validations / total_validations
                health_status['validation_success_rate'] = success_rate
                if success_rate < 0.8:  # Less than 80% success rate
                    health_status['healthy'] = False
                    health_status['warning'] = f"Low validation success rate: {success_rate:.1%}"
            
            # Update health metrics
            self.health_metrics['last_health_check'] = datetime.now()
            
            return health_status
            
        except Exception as e:
            self.health_metrics['error_count'] += 1
            return {
                'healthy': False,
                'component_id': self.component_id,
                'component_type': 'EnhancedStrategyValidator',
                'error': str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the enhanced strategy validator"""
        return {
            'component_id': self.component_id,
            'component_type': 'EnhancedStrategyValidator',
            'initialized': self.is_initialized,
            'operational': self.is_operational,
            'validation_level': self.validation_level.value,
            'enable_caching': self.enable_caching,
            'enable_performance_monitoring': self.enable_performance_monitoring,
            'enable_detailed_reporting': self.enable_detailed_reporting,
            'validation_timeout': self.validation_timeout,
            'parallel_validation': self.parallel_validation,
            'health_metrics': self.health_metrics.copy(),
            'last_error': self.last_error,
            'initialization_time': self.initialization_time,
            'start_time': self.start_time,
            'cache_size': len(self._validation_cache) if self._validation_cache else 0,
            'validation_history_size': len(self._validation_history)
        }
    
    async def validate_strategy(self, strategy: BaseStrategy, 
                               sample_data: Optional[Dict[str, pd.DataFrame]] = None,
                               run_backtest: bool = False,
                               use_cache: bool = True) -> ValidationResult:
        """Run comprehensive strategy validation"""
        
        start_time = time.time()
        
        try:
            logger.info(f"Starting validation for strategy: {strategy.strategy_id}")
            
            # Initialize result
            result = ValidationResult(
                strategy_id=strategy.strategy_id,
                validation_level=self.validation_level
            )
            
            # Code quality validation
            if self.validation_level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
                code_issues = self._validate_code_quality(strategy, result)
                result.issues.extend(code_issues)
            
            # Interface compliance validation
            interface_issues = self._validate_interface_compliance(strategy, result)
            result.issues.extend(interface_issues)
            
            # Parameter validation
            if hasattr(strategy, 'config') and strategy.config:
                param_issues = self._validate_parameters(strategy, result)
                result.issues.extend(param_issues)
            
            # Data handling validation
            if sample_data and self.validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
                data_issues = self._validate_data_handling(strategy, sample_data, result)
                result.issues.extend(data_issues)
            
            # Risk management validation
            if self.validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
                risk_issues = self._validate_risk_management(strategy, result)
                result.issues.extend(risk_issues)
            
            # Performance validation
            if self.validation_level == ValidationLevel.PRODUCTION:
                perf_issues = self._validate_performance(strategy, result)
                result.issues.extend(perf_issues)
            
            # Backtesting validation
            if run_backtest and sample_data and self.validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.PRODUCTION]:
                backtest_issues = self._validate_backtesting(strategy, sample_data, result)
                result.issues.extend(backtest_issues)
            
            # Calculate overall score and status
            self._calculate_scores(result)
            self._determine_status(result)
            
            # Generate recommendations
            self._generate_recommendations(result)
            
            # Record timing
            result.validation_time = time.time() - start_time
            
            logger.info(f"Validation completed for {strategy.strategy_id}: "
                       f"Score = {result.overall_score:.1f}, Status = {result.overall_status.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in strategy validation: {e}")
            
            result = ValidationResult(
                strategy_id=strategy.strategy_id if strategy else "unknown",
                overall_status=ValidationStatus.FAILED,
                validation_time=time.time() - start_time
            )
            result.issues.append(ValidationIssue(
                category=ValidationCategory.CODE_QUALITY,
                severity="error",
                title="Validation Error",
                description=str(e),
                validator_name="StrategyValidator"
            ))
            
            return result
    
    def _validate_code_quality(self, strategy: BaseStrategy, result: ValidationResult) -> List[ValidationIssue]:
        """Validate code quality"""
        
        issues = []
        
        try:
            # Analyze code
            code_analysis = self.code_analyzer.analyze_strategy_code(strategy)
            result.code_analysis = code_analysis
            
            if 'error' in code_analysis:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CODE_QUALITY,
                    severity="error",
                    title="Code Analysis Failed",
                    description=code_analysis['error'],
                    validator_name="CodeAnalyzer"
                ))
                return issues
            
            # Check docstring coverage
            quality = code_analysis.get('code_quality', {})
            docstring_coverage = quality.get('docstring_coverage', 0)
            
            if docstring_coverage < 0.5:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CODE_QUALITY,
                    severity="warning",
                    title="Low Docstring Coverage",
                    description=f"Only {docstring_coverage:.1%} of methods have docstrings",
                    suggestion="Add docstrings to improve code documentation",
                    validator_name="CodeAnalyzer"
                ))
            
            # Check method complexity
            avg_method_length = quality.get('average_method_length', 0)
            if avg_method_length > 50:
                issues.append(ValidationIssue(
                    category=ValidationCategory.CODE_QUALITY,
                    severity="warning",
                    title="High Method Complexity",
                    description=f"Average method length is {avg_method_length:.1f} lines",
                    suggestion="Consider breaking down complex methods into smaller functions",
                    validator_name="CodeAnalyzer"
                ))
            
            # Check type hints
            if not quality.get('has_type_hints', False):
                issues.append(ValidationIssue(
                    category=ValidationCategory.CODE_QUALITY,
                    severity="info",
                    title="Missing Type Hints",
                    description="Code lacks type hints",
                    suggestion="Add type hints to improve code clarity and IDE support",
                    validator_name="CodeAnalyzer"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating code quality: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.CODE_QUALITY,
                severity="error",
                title="Code Quality Validation Error",
                description=str(e),
                validator_name="CodeAnalyzer"
            ))
            return issues
    
    def _validate_interface_compliance(self, strategy: BaseStrategy, result: ValidationResult) -> List[ValidationIssue]:
        """Validate interface compliance"""
        
        issues = []
        
        try:
            # Check inheritance
            if not isinstance(strategy, BaseStrategy):
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTERFACE_COMPLIANCE,
                    severity="error",
                    title="Invalid Inheritance",
                    description="Strategy does not inherit from BaseStrategy",
                    suggestion="Ensure strategy class inherits from BaseStrategy",
                    validator_name="StrategyValidator"
                ))
                return issues
            
            # Check required methods
            required_methods = ['initialize', 'update', 'generate_signals']
            
            for method_name in required_methods:
                if not hasattr(strategy, method_name):
                    issues.append(ValidationIssue(
                        category=ValidationCategory.INTERFACE_COMPLIANCE,
                        severity="error",
                        title=f"Missing Required Method: {method_name}",
                        description=f"Strategy must implement {method_name} method",
                        suggestion=f"Implement the {method_name} method according to BaseStrategy interface",
                        validator_name="StrategyValidator"
                    ))
                else:
                    # Check if method is callable
                    method = getattr(strategy, method_name)
                    if not callable(method):
                        issues.append(ValidationIssue(
                            category=ValidationCategory.INTERFACE_COMPLIANCE,
                            severity="error",
                            title=f"Method Not Callable: {method_name}",
                            description=f"{method_name} is not callable",
                            validator_name="StrategyValidator"
                        ))
            
            # Test method calls
            try:
                # Test initialize
                init_result = strategy.initialize()
                if not isinstance(init_result, bool):
                    issues.append(ValidationIssue(
                        category=ValidationCategory.INTERFACE_COMPLIANCE,
                        severity="warning",
                        title="Initialize Return Type",
                        description="initialize() should return boolean",
                        suggestion="Ensure initialize() returns True/False to indicate success",
                        validator_name="StrategyValidator"
                    ))
                
            except Exception as e:
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTERFACE_COMPLIANCE,
                    severity="error",
                    title="Method Call Error",
                    description=f"Error calling strategy methods: {e}",
                    validator_name="StrategyValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating interface compliance: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.INTERFACE_COMPLIANCE,
                severity="error",
                title="Interface Validation Error",
                description=str(e),
                validator_name="StrategyValidator"
            ))
            return issues
    
    def _validate_parameters(self, strategy: BaseStrategy, result: ValidationResult) -> List[ValidationIssue]:
        """Validate strategy parameters"""
        
        issues = []
        
        try:
            # Run parameter validation
            param_validation = self.parameter_validator.validate_parameters(strategy)
            result.parameter_analysis = param_validation
            
            if 'error' in param_validation:
                issues.append(ValidationIssue(
                    category=ValidationCategory.PARAMETER_VALIDATION,
                    severity="error",
                    title="Parameter Validation Error",
                    description=param_validation['error'],
                    validator_name="ParameterValidator"
                ))
                return issues
            
            # Check for parameter issues
            for issue_msg in param_validation.get('issues', []):
                issues.append(ValidationIssue(
                    category=ValidationCategory.PARAMETER_VALIDATION,
                    severity="warning",
                    title="Parameter Issue",
                    description=issue_msg,
                    validator_name="ParameterValidator"
                ))
            
            # Check parameter count
            param_count = 0
            if 'type_checks' in param_validation:
                param_count = len(param_validation['type_checks'])
            
            if param_count == 0:
                issues.append(ValidationIssue(
                    category=ValidationCategory.PARAMETER_VALIDATION,
                    severity="warning",
                    title="No Parameters",
                    description="Strategy has no configurable parameters",
                    suggestion="Consider adding parameters to make strategy more flexible",
                    validator_name="ParameterValidator"
                ))
            elif param_count > 20:
                issues.append(ValidationIssue(
                    category=ValidationCategory.PARAMETER_VALIDATION,
                    severity="info",
                    title="Many Parameters",
                    description=f"Strategy has {param_count} parameters",
                    suggestion="Consider grouping related parameters or simplifying configuration",
                    validator_name="ParameterValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.PARAMETER_VALIDATION,
                severity="error",
                title="Parameter Validation Error",
                description=str(e),
                validator_name="ParameterValidator"
            ))
            return issues
    
    def _validate_data_handling(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame],
                              result: ValidationResult) -> List[ValidationIssue]:
        """Validate data handling"""
        
        issues = []
        
        try:
            # Run data validation
            data_validation = self.data_validator.validate_data_handling(strategy, sample_data)
            
            if 'error' in data_validation:
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_HANDLING,
                    severity="error",
                    title="Data Handling Validation Error",
                    description=data_validation['error'],
                    validator_name="DataValidator"
                ))
                return issues
            
            # Check data compatibility
            compatibility = data_validation.get('data_compatibility', {})
            
            if not compatibility.get('accepts_dict_input', False):
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_HANDLING,
                    severity="error",
                    title="Data Input Issue",
                    description="Strategy cannot process dictionary input format",
                    suggestion="Ensure update() method accepts Dict[str, pd.DataFrame]",
                    validator_name="DataValidator"
                ))
            
            # Check missing data handling
            missing_data = data_validation.get('missing_data_handling', {})
            
            if not missing_data.get('handles_missing_values', False):
                issues.append(ValidationIssue(
                    category=ValidationCategory.DATA_HANDLING,
                    severity="warning",
                    title="Missing Data Handling",
                    description="Strategy may not handle missing data properly",
                    suggestion="Add robust missing data handling logic",
                    validator_name="DataValidator"
                ))
            
            # Check performance
            performance = data_validation.get('performance_checks', {})
            processing_time = performance.get('processing_time', 0)
            
            if processing_time > 1.0:
                issues.append(ValidationIssue(
                    category=ValidationCategory.PERFORMANCE,
                    severity="warning",
                    title="Slow Data Processing",
                    description=f"Data processing took {processing_time:.2f} seconds",
                    suggestion="Optimize data processing logic for better performance",
                    validator_name="DataValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating data handling: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.DATA_HANDLING,
                severity="error",
                title="Data Handling Validation Error",
                description=str(e),
                validator_name="DataValidator"
            ))
            return issues
    
    def _validate_risk_management(self, strategy: BaseStrategy, result: ValidationResult) -> List[ValidationIssue]:
        """Validate risk management features"""
        
        issues = []
        
        try:
            # Check for risk management parameters
            risk_params = []
            if hasattr(strategy, 'config') and strategy.config:
                config_dict = strategy.config.__dict__ if hasattr(strategy.config, '__dict__') else {}
                
                # Look for common risk management parameters
                risk_keywords = ['stop_loss', 'take_profit', 'max_position', 'risk_limit', 'var_limit']
                for param_name in config_dict:
                    if any(keyword in param_name.lower() for keyword in risk_keywords):
                        risk_params.append(param_name)
            
            if not risk_params:
                issues.append(ValidationIssue(
                    category=ValidationCategory.RISK_MANAGEMENT,
                    severity="warning",
                    title="No Risk Management Parameters",
                    description="Strategy lacks explicit risk management parameters",
                    suggestion="Consider adding stop loss, position limits, or other risk controls",
                    validator_name="StrategyValidator"
                ))
            
            # Check for risk management methods
            risk_methods = ['calculate_position_size', 'check_risk_limits', 'apply_risk_controls']
            found_risk_methods = []
            
            for method_name in risk_methods:
                if hasattr(strategy, method_name):
                    found_risk_methods.append(method_name)
            
            if not found_risk_methods:
                issues.append(ValidationIssue(
                    category=ValidationCategory.RISK_MANAGEMENT,
                    severity="info",
                    title="No Explicit Risk Methods",
                    description="Strategy lacks explicit risk management methods",
                    suggestion="Consider implementing risk management methods like calculate_position_size()",
                    validator_name="StrategyValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating risk management: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.RISK_MANAGEMENT,
                severity="error",
                title="Risk Management Validation Error",
                description=str(e),
                validator_name="StrategyValidator"
            ))
            return issues
    
    def _validate_performance(self, strategy: BaseStrategy, result: ValidationResult) -> List[ValidationIssue]:
        """Validate strategy performance characteristics"""
        
        issues = []
        
        try:
            # Test initialization performance
            start_time = time.time()
            try:
                strategy.initialize()
                init_time = time.time() - start_time
                
                if init_time > 5.0:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.PERFORMANCE,
                        severity="warning",
                        title="Slow Initialization",
                        description=f"Strategy initialization took {init_time:.2f} seconds",
                        suggestion="Optimize initialization logic",
                        validator_name="StrategyValidator"
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    category=ValidationCategory.PERFORMANCE,
                    severity="error",
                    title="Initialization Error",
                    description=f"Strategy initialization failed: {e}",
                    validator_name="StrategyValidator"
                ))
            
            # Check memory usage (simplified)
            import sys
            strategy_size = sys.getsizeof(strategy)
            
            if strategy_size > 1024 * 1024:  # 1MB
                issues.append(ValidationIssue(
                    category=ValidationCategory.PERFORMANCE,
                    severity="info",
                    title="Large Memory Footprint",
                    description=f"Strategy object size is {strategy_size / 1024:.1f} KB",
                    suggestion="Consider optimizing memory usage",
                    validator_name="StrategyValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating performance: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.PERFORMANCE,
                severity="error",
                title="Performance Validation Error",
                description=str(e),
                validator_name="StrategyValidator"
            ))
            return issues
    
    def _validate_backtesting(self, strategy: BaseStrategy, sample_data: Dict[str, pd.DataFrame],
                            result: ValidationResult) -> List[ValidationIssue]:
        """Validate strategy through basic signal generation test"""
        
        issues = []
        
        try:
            # Simple signal generation test instead of full backtest
            if sample_data:
                symbol = list(sample_data.keys())[0]
                data = sample_data[symbol]
                
                # Test signal generation
                signals = strategy.generate_signals(data)
                
                if signals is not None and len(signals) > 0:
                    result.backtest_results = {
                        'signal_count': len(signals),
                        'total_trades': len(signals),
                        'errors': [],
                        'warnings': []
                    }
                else:
                    result.backtest_results = {
                        'signal_count': 0,
                        'total_trades': 0,
                        'errors': [],
                        'warnings': ['No signals generated']
                    }
                    
                    issues.append(ValidationIssue(
                        category=ValidationCategory.BACKTESTING,
                        severity="warning",
                        title="No Signals Generated",
                        description="Strategy generated no signals during validation",
                        suggestion="Check signal generation logic",
                        validator_name="StrategyValidator"
                    ))
            else:
                issues.append(ValidationIssue(
                    category=ValidationCategory.BACKTESTING,
                    severity="error",
                    title="No Sample Data",
                    description="No sample data provided for backtesting validation",
                    validator_name="StrategyValidator"
                ))
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating backtesting: {e}")
            issues.append(ValidationIssue(
                category=ValidationCategory.BACKTESTING,
                severity="error",
                title="Backtesting Validation Error",
                description=str(e),
                validator_name="StrategyValidator"
            ))
            return issues
    
    def _calculate_scores(self, result: ValidationResult) -> None:
        """Calculate validation scores"""
        
        try:
            # Count issues by category and severity
            category_scores = {}
            
            for category in ValidationCategory:
                total_points = 100
                error_penalty = 50
                warning_penalty = 20
                info_penalty = 5
                
                category_issues = [issue for issue in result.issues if issue.category == category]
                
                penalties = 0
                for issue in category_issues:
                    if issue.severity == "error":
                        penalties += error_penalty
                    elif issue.severity == "warning":
                        penalties += warning_penalty
                    elif issue.severity == "info":
                        penalties += info_penalty
                
                score = max(0, total_points - penalties)
                category_scores[category] = score
            
            result.category_scores = category_scores
            
            # Calculate overall score using weights
            weighted_score = 0
            total_weight = 0
            
            for category, weight in self.validation_weights.items():
                if category in category_scores:
                    weighted_score += category_scores[category] * weight
                    total_weight += weight
            
            if total_weight > 0:
                result.overall_score = weighted_score / total_weight
            else:
                result.overall_score = 0
            
        except Exception as e:
            logger.error(f"Error calculating scores: {e}")
            result.overall_score = 0
    
    def _determine_status(self, result: ValidationResult) -> None:
        """Determine overall validation status"""
        
        try:
            # Check for errors
            errors = [issue for issue in result.issues if issue.severity == "error"]
            warnings = [issue for issue in result.issues if issue.severity == "warning"]
            
            if errors:
                result.overall_status = ValidationStatus.FAILED
            elif result.overall_score >= 80:
                result.overall_status = ValidationStatus.PASSED
            elif result.overall_score >= 60 or warnings:
                result.overall_status = ValidationStatus.WARNING
            else:
                result.overall_status = ValidationStatus.FAILED
            
        except Exception as e:
            logger.error(f"Error determining status: {e}")
            result.overall_status = ValidationStatus.FAILED
    
    def _generate_recommendations(self, result: ValidationResult) -> None:
        """Generate recommendations based on validation results"""
        
        try:
            recommendations = []
            
            # Analyze issues and generate recommendations
            error_count = len([issue for issue in result.issues if issue.severity == "error"])
            warning_count = len([issue for issue in result.issues if issue.severity == "warning"])
            
            if error_count > 0:
                recommendations.append(f"Fix {error_count} critical error(s) before using this strategy")
            
            if warning_count > 5:
                recommendations.append("Address multiple warnings to improve strategy reliability")
            
            # Category-specific recommendations
            code_score = result.category_scores.get(ValidationCategory.CODE_QUALITY, 100)
            if code_score < 70:
                recommendations.append("Improve code quality with better documentation and structure")
            
            param_score = result.category_scores.get(ValidationCategory.PARAMETER_VALIDATION, 100)
            if param_score < 80:
                recommendations.append("Review and validate strategy parameters")
            
            risk_score = result.category_scores.get(ValidationCategory.RISK_MANAGEMENT, 100)
            if risk_score < 60:
                recommendations.append("Implement comprehensive risk management controls")
            
            # Score-based recommendations
            if result.overall_score < 60:
                recommendations.append("Strategy requires significant improvements before production use")
            elif result.overall_score < 80:
                recommendations.append("Strategy is acceptable but could benefit from optimization")
            else:
                recommendations.append("Strategy meets validation requirements")
            
            result.recommendations = recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            result.recommendations = ["Unable to generate recommendations due to validation error"]
    
    def export_validation_report(self, result: ValidationResult, format_type: str = "json") -> str:
        """Export validation report to file"""
        
        try:
            output_dir = Path("validation_reports")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"validation_{result.strategy_id}_{timestamp}"
            
            if format_type == "json":
                import json
                
                output_path = output_dir / f"{filename}.json"
                
                # Prepare data for JSON serialization
                export_data = {
                    'strategy_id': result.strategy_id,
                    'validation_level': result.validation_level.value,
                    'overall_status': result.overall_status.value,
                    'overall_score': result.overall_score,
                    'category_scores': {cat.value: score for cat, score in result.category_scores.items()},
                    'total_issues': len(result.issues),
                    'error_count': len([i for i in result.issues if i.severity == "error"]),
                    'warning_count': len([i for i in result.issues if i.severity == "warning"]),
                    'recommendations': result.recommendations,
                    'validation_time': result.validation_time,
                    'timestamp': result.validation_timestamp.isoformat()
                }
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
            elif format_type == "csv":
                output_path = output_dir / f"{filename}_summary.csv"
                
                # Create summary DataFrame
                summary_data = {
                    'Metric': ['Overall Score', 'Status', 'Total Issues', 'Errors', 'Warnings', 'Validation Time'],
                    'Value': [
                        f"{result.overall_score:.1f}",
                        result.overall_status.value,
                        len(result.issues),
                        len([i for i in result.issues if i.severity == "error"]),
                        len([i for i in result.issues if i.severity == "warning"]),
                        f"{result.validation_time:.2f}s"
                    ]
                }
                
                df = pd.DataFrame(summary_data)
                df.to_csv(output_path, index=False)
            
            logger.info(f"Validation report exported: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error exporting validation report: {e}")
            return ""
    
    # Enhanced Internal Methods
    async def _initialize_caching_system(self) -> None:
        """Initialize enhanced caching system"""
        try:
            if self.enable_caching:
                self._validation_cache = {}
                logger.info("📋 Enhanced validation caching system initialized")
        except Exception as e:
            logger.warning(f"Caching system initialization failed: {e}")
    
    async def _initialize_performance_monitoring(self) -> None:
        """Initialize performance monitoring"""
        try:
            if self.enable_performance_monitoring:
                self._monitoring_task = None
                logger.info("📊 Performance monitoring initialized")
        except Exception as e:
            logger.warning(f"Performance monitoring initialization failed: {e}")
    
    async def _initialize_benchmarking_system(self) -> None:
        """Initialize benchmarking system"""
        try:
            self._performance_benchmarks = {
                'validation_time_percentiles': {},
                'score_distributions': {},
                'common_issues': {},
                'best_practices': {}
            }
            logger.info("🎯 Benchmarking system initialized")
        except Exception as e:
            logger.warning(f"Benchmarking system initialization failed: {e}")
    
    async def _load_validation_benchmarks(self) -> None:
        """Load validation benchmarks from historical data"""
        try:
            # Load benchmarks from file or database
            # This is a placeholder for actual benchmark loading
            logger.info("📈 Validation benchmarks loaded")
        except Exception as e:
            logger.warning(f"Benchmark loading failed: {e}")
    
    async def _start_performance_monitoring(self) -> None:
        """Start performance monitoring task"""
        try:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("📊 Performance monitoring started")
        except Exception as e:
            logger.warning(f"Performance monitoring start failed: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Performance monitoring loop"""
        while self.is_operational:
            try:
                await self._update_performance_benchmarks()
                await self._cleanup_validation_cache()
                await asyncio.sleep(300)  # Monitor every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(600)  # Longer wait on error
    
    async def _save_validation_data(self) -> None:
        """Save validation history and benchmarks"""
        try:
            # Save validation history to file
            history_file = Path("validation_history.json")
            with open(history_file, 'w') as f:
                json.dump(list(self._validation_history), f, indent=2, default=str)
            
            # Save performance benchmarks
            benchmarks_file = Path("validation_benchmarks.json")
            with open(benchmarks_file, 'w') as f:
                json.dump(self._performance_benchmarks, f, indent=2, default=str)
            
            logger.info("💾 Validation data saved successfully")
            
        except Exception as e:
            logger.error(f"Validation data save failed: {e}")
    
    async def _update_performance_benchmarks(self) -> None:
        """Update performance benchmarks from validation history"""
        try:
            if not self._validation_history:
                return
            
            # Update validation time percentiles
            validation_times = [entry['validation_time'] for entry in self._validation_history]
            if validation_times:
                self._performance_benchmarks['validation_time_percentiles'] = {
                    'p50': np.percentile(validation_times, 50),
                    'p90': np.percentile(validation_times, 90),
                    'p95': np.percentile(validation_times, 95),
                    'p99': np.percentile(validation_times, 99)
                }
            
            # Update score distributions
            scores = [entry['overall_score'] for entry in self._validation_history]
            if scores:
                self._performance_benchmarks['score_distributions'] = {
                    'mean': np.mean(scores),
                    'std': np.std(scores),
                    'min': np.min(scores),
                    'max': np.max(scores),
                    'p25': np.percentile(scores, 25),
                    'p75': np.percentile(scores, 75)
                }
            
        except Exception as e:
            logger.error(f"Performance benchmark update failed: {e}")
    
    async def _cleanup_validation_cache(self) -> None:
        """Clean up old validation cache entries"""
        try:
            if not self._validation_cache:
                return
            
            current_time = datetime.now()
            expired_keys = []
            
            for strategy_id, cache_entry in self._validation_cache.items():
                if (current_time - cache_entry['timestamp']).total_seconds() > 3600:  # 1 hour TTL
                    expired_keys.append(strategy_id)
            
            for key in expired_keys:
                del self._validation_cache[key]
            
            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired validation cache entries")
                
        except Exception as e:
            logger.error(f"Validation cache cleanup failed: {e}")
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive validation statistics"""
        try:
            stats = {
                'total_validations': len(self._validation_history),
                'performance_metrics': self.health_metrics['performance_metrics'].copy(),
                'performance_benchmarks': self._performance_benchmarks.copy(),
                'cache_statistics': {
                    'cache_size': len(self._validation_cache) if self._validation_cache else 0,
                    'cache_hit_rate': 0.0
                }
            }
            
            # Calculate cache hit rate
            total_cache_requests = (self.health_metrics['performance_metrics']['validation_cache_hits'] + 
                                  self.health_metrics['performance_metrics']['validation_cache_misses'])
            if total_cache_requests > 0:
                stats['cache_statistics']['cache_hit_rate'] = (
                    self.health_metrics['performance_metrics']['validation_cache_hits'] / total_cache_requests
                )
            
            # Add recent validation trends
            if self._validation_history:
                recent_validations = list(self._validation_history)[-50:]  # Last 50 validations
                stats['recent_trends'] = {
                    'avg_score': np.mean([v['overall_score'] for v in recent_validations]),
                    'avg_time': np.mean([v['validation_time'] for v in recent_validations]),
                    'success_rate': len([v for v in recent_validations if v['status'] != 'failed']) / len(recent_validations)
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Statistics generation failed: {e}")
            return {}


# Maintain backward compatibility
StrategyValidator = EnhancedStrategyValidator