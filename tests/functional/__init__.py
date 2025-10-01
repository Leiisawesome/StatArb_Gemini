"""
Functional Testing Module for StatArb_Gemini Core Engine

This module provides comprehensive end-to-end functional testing that validates
complete trading logic flow using real market data through all integrated
core engine components.

Key Components:
- EndToEndFunctionalTester: Complete trading scenario testing
- DataFlowValidator: Data integrity validation across components
- TradingLogicValidator: Business logic and strategy performance validation

Usage:
    from tests.functional import EndToEndFunctionalTester, DataFlowValidator
    
    # Run comprehensive functional tests
    tester = EndToEndFunctionalTester(config)
    results = await tester.run_comprehensive_functional_tests()
    
    # Run data flow validation only
    validator = DataFlowValidator(integration_manager)
    validation = await validator.validate_complete_data_flow()
"""

from .end_to_end_functional_tester import (
    EndToEndFunctionalTester,
    FunctionalTestResult,
    TradingScenarioConfig
)

from .data_flow_validator import (
    DataFlowValidator,
    DataFlowValidationResult,
    DataFlowCheckpoint
)

from .trading_logic_validator import (
    TradingLogicValidator,
    TradingLogicValidationResult
)

__all__ = [
    'EndToEndFunctionalTester',
    'FunctionalTestResult', 
    'TradingScenarioConfig',
    'DataFlowValidator',
    'DataFlowValidationResult',
    'DataFlowCheckpoint',
    'TradingLogicValidator',
    'TradingLogicValidationResult'
]

__version__ = '1.0.0'
__author__ = 'StatArb_Gemini Development Team'
__description__ = 'End-to-End Functional Testing Framework for Core Engine'
