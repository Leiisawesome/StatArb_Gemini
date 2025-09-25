"""
Strategy Test Suite Package
==========================

This package contains comprehensive testing and validation tools for all trading strategies
in the StatArb_Gemini system.

Test Scripts:
- academic_model_validation.py: Academic compliance and mathematical model validation
- comprehensive_strategy_validation.py: Comprehensive strategy assessment and validation
- strategy_implementation_audit.py: Strategy implementation audit and compliance checking
- strategy_improvement_tracker.py: Strategy performance improvement tracking
- strategy_test_suite.py: Main comprehensive test suite for all strategies

Note: institutional_trade_simulation.py is located in the project root directory.

Usage:
    cd tests/strategy_test/
    python strategy_test_suite.py  # Run comprehensive test suite
    python academic_model_validation.py  # Run academic validation
    cd ../../ && python institutional_trade_simulation.py  # Run institutional simulation from root

Author: AI Assistant (Professional Quant & System Architect)
Date: September 2025
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"

# Import main test classes for easy access
try:
    from .strategy_test_suite import StrategyTestFramework
    from .comprehensive_strategy_validation import ComprehensiveStrategyValidator
    # Note: InstitutionalTradeSimulator is in root directory
    
    __all__ = [
        'StrategyTestFramework',
        'ComprehensiveStrategyValidator'
    ]
except ImportError:
    # Handle import errors gracefully during development
    __all__ = []
