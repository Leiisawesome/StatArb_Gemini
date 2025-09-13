"""
IBKR Integration Tests
=====================

Comprehensive test suite for Interactive Brokers (IBKR) integration.

This module contains all tests for IBKR broker integration including:
- Connection diagnostics
- Simple connection tests  
- Real connection tests with advanced order management
- Multi-broker routing tests
- Performance analytics tests

Test Files:
- ibkr_connection_diagnostics.py: Network and API diagnostics
- ibkr_simple_test.py: Basic connection and account tests
- ibkr_real_test.py: Comprehensive integration tests
- ibkr_api_test.py: Direct API connection tests
- ibkr_client_id_test.py: Client ID testing
- run_ibkr_tests.py: Unified test runner

Usage:
    # Run all IBKR tests
    python tests/integration/ibkr/run_ibkr_tests.py --test comprehensive
    
    # Run specific tests
    python tests/integration/ibkr/run_ibkr_tests.py --test diagnostics
    python tests/integration/ibkr/run_ibkr_tests.py --test simple
    python tests/integration/ibkr/run_ibkr_tests.py --test real

Prerequisites:
- IB Gateway running and logged in
- API connections enabled in IB Gateway
- Paper trading account active
"""

__version__ = "1.0.0"
__author__ = "Professional Trading System Architecture"
